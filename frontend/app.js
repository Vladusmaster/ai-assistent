const chatHistory = document.getElementById('chatHistory');
const userInput = document.getElementById('userInput');
const loader = document.getElementById('loader');

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    addMessage(text, 'user-msg');
    userInput.value = '';
    loader.style.display = 'block';

    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: text })
        });

        if (!response.ok) throw new Error('Ошибка сервера');
        
        const data = await response.json();
        let botReply = '';

        if (data.status === 'error') {
            botReply = `<p style="color: #c53030; font-weight: bold; margin: 0;">⚠️ ${data.message}</p>`;
        } else {
            if (data.summary) {
                botReply += `<p style="margin-top: 0;"><b>Ответ:</b> ${data.summary}</p>`;
            }
            
            botReply += `<b>Сгенерированный SQL:</b><div class="sql-box">${data.sql}</div>`;
            
            if (data.explanation) {
                const exp = data.explanation;
                botReply += `
                    <div class="explain-box">
                        <b>Explainable AI:</b>
                        <ul>
                            <li><b>Таблицы:</b> ${(exp.tables || []).join(', ') || 'нет'}</li>
                            <li><b>Связи (JOIN):</b> ${(exp.joins || []).join('; ') || 'нет'}</li>
                            <li><b>Фильтры:</b> ${(exp.filters || []).join('; ') || 'нет'}</li>
                            <li><b>Агрегации:</b> ${(exp.aggregations || []).join('; ') || 'нет'}</li>
                        </ul>
                    </div>
                `;
            }

            if (data.columns && data.data) {
                if (data.data.length === 0) {
                    botReply += '<p style="margin-top: 10px;"><i>Данных по заданному условию не найдено.</i></p>';
                } else {
                    botReply += '<div class="table-wrap"><table><thead><tr>';
                    data.columns.forEach(col => {
                        botReply += `<th>${col}</th>`;
                    });
                    botReply += '</tr></thead><tbody>';
                    
                    data.data.forEach(row => {
                        botReply += '<tr>';
                        data.columns.forEach(col => {
                            const val = row[col];
                            botReply += `<td>${val !== null && val !== undefined ? val : ''}</td>`;
                        });
                        botReply += '</tr>';
                    });
                    botReply += '</tbody></table></div>';
                    botReply += `<small style="color: #718096; display: block; margin-top: 5px;">Показано записей: ${data.count}</small>`;
                }
            }
        }

        botReply += `
            <details>
                <summary>Исходный JSON</summary>
                <pre>${JSON.stringify(data, null, 2)}</pre>
            </details>
        `;

        addMessage(botReply, 'bot-msg');

    } catch (error) {
        addMessage('<span style="color: #c53030;">Ошибка подключения к бэкенду. Проверьте статус сервера.</span>', 'bot-msg');
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