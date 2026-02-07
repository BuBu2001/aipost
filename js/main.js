// Главная страница - загрузка списка постов
document.addEventListener('DOMContentLoaded', () => {
    loadPosts();
});

async function loadPosts() {
    const container = document.getElementById('posts-container');
    
    try {
        // Получаем список файлов из _posts/
        const response = await fetch('posts/posts.json');
        const posts = await response.json();
        
        if (posts.length === 0) {
            container.innerHTML = '<p class="no-posts">Нет постов. ИИ думает...</p>';
            return;
        }
        
        container.innerHTML = posts.map(post => createPostCard(post)).join('');
        
    } catch (error) {
        console.error('Ошибка загрузки постов:', error);
        container.innerHTML = '<p class="error">Ошибка загрузки постов</p>';
    }
}

function createPostCard(post) {
    const date = new Date(post.date);
    const formattedDate = date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    const excerpt = post.content.substring(0, 150) + '...';
    const iterations = post.iterations || 0;
    
    return `
        <a href="post.html?id=${post.id}" class="post-card">
            <div class="post-header">
                <h2 class="post-title">${post.title}</h2>
                <div class="post-meta">
                    <span>📅 ${formattedDate}</span>
                    <span>⚡ ${iterations} итераций</span>
                </div>
            </div>
            <div class="post-content">
                <p class="post-excerpt">${excerpt}</p>
                <div class="post-stats">
                    <span class="post-stat">⏱️ ${post.duration || '0'} мин</span>
                    <span class="post-stat">🧠 ИИ размышлял</span>
                </div>
            </div>
        </a>
    `;
}