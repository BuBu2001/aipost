import requests
import json
import os
from datetime import datetime
import subprocess
import time
import re
import signal
import sys

# ===== НАСТРОЙКИ =====
LLAMA_URL = "http://localhost:8081/completion"
MODEL_TEMPERATURE = 0.8
MAX_ITERATIONS = 50  # Максимум итераций (можно прервать раньше)

# Глобальная переменная для отслеживания прерывания
running = True

def signal_handler(sig, frame):
    global running
    print("\n\n🛑 Получен сигнал остановки. Завершаю текущую итерацию...")
    running = False
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def slugify(text):
    """Превращает текст в безопасное имя файла"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9а-яё]+', '-', text)
    text = text.strip('-')
    return text[:50]

def ask_llama(prompt, context=""):
    """Отправляет запрос в llama-server"""
    full_prompt = f"""Контекст предыдущих размышлений:
{context}

Тема для размышления: {prompt}

Продолжи размышление. Не давай финальный ответ. Думай шаг за шагом, выдвигай новые идеи, сомневайся, анализируй противоречия. Пиши 3-5 предложений."""

    payload = {
        "prompt": full_prompt,
        "temperature": MODEL_TEMPERATURE,
        "max_tokens": 400,
        "stop": ["\n\n\n", "###", "Итерация"]
    }
    
    try:
        response = requests.post(LLAMA_URL, json=payload, timeout=180)
        result = response.json()
        return result.get("content", "").strip()
    except Exception as e:
        print(f"❌ Ошибка llama-server: {e}")
        return ""

def ensure_posts_folder():
    """Создаёт папку posts если её нет"""
    posts_dir = "posts"
    if not os.path.exists(posts_dir):
        os.makedirs(posts_dir)
        print(f"📁 Создана папка: {os.path.abspath(posts_dir)}")
    return posts_dir

def save_iteration(topic, iteration_num, thought, all_thoughts, post_id):
    """Сохраняет текущую итерацию в файл поста"""
    posts_dir = ensure_posts_folder()
    
    # Формируем данные поста
    post_data = {
        "id": post_id,
        "title": topic,
        "date": datetime.now().isoformat(),
        "thoughts": all_thoughts,
        "conclusion": thought,
        "totalDuration": iteration_num * 2,
        "currentIteration": iteration_num
    }
    
    # Сохраняем файл поста
    post_path = os.path.join(posts_dir, f"{post_id}.json")
    with open(post_path, 'w', encoding='utf-8') as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ Итерация #{iteration_num} сохранена: {post_path}")
    
    # Обновляем индекс
    index_path = os.path.join(posts_dir, "posts.json")
    
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
    else:
        index = []
    
    # Обновляем существующий пост или добавляем новый
    found = False
    for item in index:
        if item["id"] == post_id:
            item["title"] = topic
            item["date"] = post_data["date"]
            item["content"] = thought[:200] + "..."
            item["iterations"] = iteration_num
            item["duration"] = post_data["totalDuration"]
            found = True
            break
    
    if not found:
        index.insert(0, {
            "id": post_id,
            "title": topic,
            "date": post_data["date"],
            "content": thought[:200] + "...",
            "iterations": iteration_num,
            "duration": post_data["totalDuration"]
        })
    
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ Индекс обновлён: {index_path}")
    return post_id

def git_commit_and_push(post_id, iteration_num):
    """Коммитит и пушит изменения в репозиторий"""
    try:
        # Проверяем статус Git
        result = subprocess.run(['git', 'status'], capture_output=True, text=True)
        if "fatal: not a git repository" in result.stderr:
            print("  ❌ Ошибка: это не Git-репозиторий!")
            print(f"     Текущая папка: {os.getcwd()}")
            return False
        
        # Добавляем файлы
        subprocess.run(['git', 'add', 'posts/'], check=True, capture_output=True)
        
        # Проверяем, есть ли изменения для коммита
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True)
        if result.returncode == 0:
            print("  ℹ️ Нет изменений для коммита")
            return True
        
        # Делаем коммит
        commit_msg = f"experiment: итерация #{iteration_num}"
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True, capture_output=True)
        
        # Определяем имя ветки (master или main)
        branch_result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                     capture_output=True, text=True)
        branch = branch_result.stdout.strip()
        
        # Пушим
        subprocess.run(['git', 'push', 'origin', branch], check=True, capture_output=True)
        
        print(f"  ✓ Опубликовано на GitHub (ветка: {branch})")
        print(f"  🌐 Сайт обновится через 1-2 минуты: https://bubu2001.github.io/aipost/")
        return True
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
        print(f"  ⚠️ Ошибка Git:")
        print(f"     {error_msg[:400]}")
        return False
    except Exception as e:
        print(f"  ⚠️ Неизвестная ошибка Git: {e}")
        return False

def run_thinking_experiment(topic):
    """Основной цикл размышлений над ОДНОЙ темой"""
    global running
    
    print(f"\n🧠 ЭКСПЕРИМЕНТ: {topic}")
    print("=" * 70)
    print("Первые 3 итерации будут сгенерированы быстро (каждые 30 сек)")
    print("Последующие — каждые 2 часа")
    print("Чтобы остановить: нажми Ctrl+C в любое время")
    print("=" * 70 + "\n")
    
    # Проверяем, что мы в папке репозитория
    if not os.path.exists(".git"):
        print(f"❌ Ошибка: папка '.git' не найдена!")
        print(f"   Текущая директория: {os.getcwd()}")
        print(f"   Запусти скрипт из папки репозитория:")
        print(f"   cd C:\\Users\\g\\Documents\\aipost")
        print(f"   python ai_orchestrator.py")
        return
    
    print(f"📁 Рабочая директория: {os.getcwd()}")
    print(f"📁 Папка posts: {os.path.abspath('posts')}")
    print()
    
    # Проверяем llama-server
    try:
        requests.get("http://localhost:8081", timeout=5)
        print("✓ llama-server доступен на порту 8081")
    except:
        print("❌ Ошибка: llama-server не запущен")
        print("\nЗапусти в отдельном окне терминала:")
        print('"C:/Users/g/AppData/Local/Microsoft/WinGet/Packages/ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe/llama-server.exe" -m "C:/Users/g/Documents/Triple compatibility of models/TCM/Local_AI_models/Qwen3-0.6B-Q8_0.gguf" --port 8081')
        return
    
    # Генерируем ID поста один раз для всей цепочки
    post_id = datetime.now().strftime('%Y-%m-%d') + '-' + slugify(topic)
    print(f"\n🆔 ID поста: {post_id}\n")
    
    all_thoughts = []
    context = f"Тема: {topic}\n\nНачало размышления:"
    
    for iteration in range(1, MAX_ITERATIONS + 1):
        if not running:
            print("\n⏹️ Эксперимент остановлен пользователем")
            print(f"✅ Завершено {iteration-1} итераций")
            print(f"🌐 Последний результат: https://bubu2001.github.io/aipost/")
            return
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Итерация #{iteration}")
        print("-" * 70)
        
        # Генерируем мысль
        thought = ask_llama(topic, context)
        
        if not thought:
            print("⚠️ Не удалось сгенерировать мысль. Повторная попытка через 10 сек...")
            time.sleep(10)
            continue
        
        print(f"\n{thought}\n")
        
        # Сохраняем
        all_thoughts.append({
            "iteration": iteration,
            "text": thought,
            "timestamp": datetime.now().isoformat(),
            "duration": 0
        })
        
        # Обновляем контекст
        context += f"\n\nИтерация #{iteration}:\n{thought}"
        
        # Сохраняем на диск и публикуем
        save_iteration(topic, iteration, thought, all_thoughts, post_id)
        git_commit_and_push(post_id, iteration)
        
        # Определяем паузу
        if iteration < 3:
            pause = 30  # секунд для первых 3 итераций
            print(f"\n⏱️ Следующая итерация через {pause} секунд...")
        else:
            pause = 7200  # 2 часа для остальных
            print(f"\n⏳ Следующая итерация через 2 часа...")
            print("   Чтобы остановить эксперимент: нажми Ctrl+C")
        
        # Ждём с возможностью прерывания
        start_time = time.time()
        while time.time() - start_time < pause:
            if not running:
                break
            time.sleep(1)
    
    print("\n✅ Достигнут лимит итераций")
    print(f"🌐 Финальный результат: https://bubu2001.github.io/aipost/")

# ===== ЗАПУСК =====
if __name__ == "__main__":
    print("=" * 70)
    print("🤖 AI BLOG EXPERIMENT — постепенное размышление над одной темой")
    print("=" * 70)
    
    # Запрашиваем тему у пользователя
    topic = input("\n❓ Введи тему для размышления ИИ: ").strip()
    
    if not topic:
        print("❌ Тема не может быть пустой")
        exit()
    
    run_thinking_experiment(topic)