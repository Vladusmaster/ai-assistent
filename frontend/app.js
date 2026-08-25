const chatHistory = document.getElementById('chatHistory');
const userInput = document.getElementById('userInput');
const loader = document.getElementById('loader');

function handleKeyPress(event) {
    if (event.key === 'Enter') sendMessage();
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    addMessage(text, 'user-msg');
    userInput.value = '';
    loader.style.display = 'block';

    try {
        const response = await fetch('http://127.0.0.1:8000/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: text }) // Упаковываем в JSON для отправки
        });

        if (!response.ok) throw new Error('Ошибка сервера');
        
        const data = await response.json(); // Распаковываем полученный JSON
        
        let botReply = `<p><b>Сгенерированный SQL:</b> <code>${data.generated_sql || 'Не сгенерирован'}</code></p>`;
        
        if (data.status === 'error') {
            botReply += `<p style="color: #c53030; font-weight: bold;">Ошибка: ${data.message}</p>`;
        } else if (data.columns && data.rows) {
            // ... (вся остальная логика отрисовки таблицы) ...
        }

        // Блок с исходным JSON
        botReply += `
            <details>
                <summary>Показать исходный JSON ответа</summary>
                <pre>${JSON.stringify(data, null, 2)}</pre>
            </details>
        `;

        addMessage(botReply, 'bot-msg');

    } catch (error) {
        addMessage('<span style="color: #c53030;">Произошла ошибка при подключении к серверу.</span>', 'bot-msg');
        console.error(error);
    } finally {
        loader.style.display = 'none';
    }
}

function addMessage(htmlContent, className) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${className}`;
    msgDiv.innerHTML = htmlContent;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight; 
}