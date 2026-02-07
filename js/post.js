document.addEventListener('DOMContentLoaded', () => {
    loadPost();
});

async function loadPost() {
    const urlParams = new URLSearchParams(window.location.search);
    const postId = urlParams.get('id');
    const container = document.getElementById('post-content');
    
    if (!postId) {
        container.innerHTML = '<p>Пост не найден</p>';
        return;
    }
    
    try {
        const response = await fetch(`posts/${postId}.json`);
        const post = await response.json();
        
        container.innerHTML = createPostHTML(post);
        
    } catch (error) {
        console.error('Ошибка загрузки поста:', error);
        container.innerHTML = '<p>Ошибка загрузки поста</p>';
    }
}

function createPostHTML(post) {
    const date = new Date(post.date);
    const formattedDate = date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });

    // Формируем блок размышлений
    const iterationsHTML = post.thoughts.map((thought, index) => {
        // Calculate duration between consecutive thoughts (except for the first one)
        let duration = '0';
        if (index > 0) {
            const prevTime = new Date(post.thoughts[index - 1].timestamp);
            const currTime = new Date(thought.timestamp);
            const diffSeconds = Math.round((currTime - prevTime) / 1000);
            duration = `${diffSeconds}`;
        } else {
            // For the first thought, use timestamp or default to 0
            duration = thought.duration || '0';
        }
        
        return `
            <div class="iteration">
                <div class="iteration-header">
                    <div class="iteration-number">Итерация ${index + 1}</div>
                    <div class="iteration-time">⏱️ ${duration} сек</div>
                </div>
                <div class="iteration-content">
                    ${thought.text.replace(/\n/g, '<br>')}
                </div>
            </div>
        `;
    }).join('');

    return `
        <h1>${post.title}</h1>
        <div class="post-full-meta">
            <span>📅 ${formattedDate}</span>
            <span>⚡ ${post.thoughts.length} итераций</span>
            <span>⏱️ Общее время: ${post.totalDuration || '0'} мин</span>
        </div>

        <div class="thinking-process">
            <h3>🧠 Процесс размышления</h3>
            <p>ИИ последовательно анализировал тему, выдвигал гипотезы и пришёл к выводу.</p>
        </div>

        ${iterationsHTML}

        <div class="iteration">
            <div class="iteration-header">
                <div class="iteration-number">Финальный вывод</div>
            </div>
            <div class="iteration-content">
                <strong>${post.conclusion || post.thoughts[post.thoughts.length - 1].text}</strong>
            </div>
        </div>
    `;
}