const chatOverlay = document.getElementById('chatOverlay');
const chatHistory = document.getElementById('chatHistory');
const userInput = document.getElementById('userInput');
const loader = document.getElementById('loader');
const sendBtn = document.getElementById('sendBtn');

function toggleChat(forceState) {
    const isVisible = chatOverlay.style.display === 'flex';
    const newState = forceState !== undefined ? forceState : !isVisible;
    
    chatOverlay.style.display = newState ? 'flex' : 'none';
    if (newState) {
        setTimeout(() => userInput.focus(), 150);
    }
}

function handleOverlayClick(event) {
    if (event.target === chatOverlay) {
        toggleChat(false);
    }
}

function clearChat() {
    chatHistory.innerHTML = `
        <div class="message bot-msg">
            <div class="msg-content">
                Диалог очищен. Задайте новый вопрос к базе данных РЭУ им. Г.В. Плеханова.
            </div>
        </div>
    `;
}

function quickSend(promptText) {
    userInput.value = promptText;
    sendMessage();
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function copySql(btn) {
    const codeBlock = btn.closest('.sql-card').querySelector('.sql-code');
    navigator.clipboard.writeText(codeBlock.innerText).then(() => {
        btn.innerText = 'Скопировано';
        setTimeout(() => btn.innerText = 'Копировать', 1500);
    });
}

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    appendUserMessage(text);
    userInput.value = '';

    userInput.disabled = true;
    sendBtn.disabled = true;
    loader.style.display = 'flex';
    chatHistory.scrollTop = chatHistory.scrollHeight;

    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: text })
        });

        if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
        
        const data = await response.json();
        renderBotResponse(data);

    } catch (error) {
        appendBotHtml(`
            <div class="error-card">
                ⚠️ Сбой обработки запроса: ${escapeHtml(error.message)}. Проверьте доступность бэкенда.
            </div>
        `);
    } finally {
        loader.style.display = 'none';
        userInput.disabled = false;
        sendBtn.disabled = false;
        userInput.focus();
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
}

function appendUserMessage(text) {
    const div = document.createElement('div');
    div.className = 'message user-msg';
    div.innerText = text;
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function appendBotHtml(html) {
    const div = document.createElement('div');
    div.className = 'message bot-msg';
    div.innerHTML = html;
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function renderBotResponse(data) {
    if (data.status === 'error') {
        appendBotHtml(`
            <div class="error-card">
                ⚠️ <b>Отклонено системой безопасности:</b> ${escapeHtml(data.message)}
            </div>
        `);
        return;
    }

    let html = '';

    const summaryText = data.summary || data.summary_ru;
    if (summaryText) {
        html += `<div class="bot-summary-box"><b>Результат:</b> ${escapeHtml(summaryText)}</div>`;
    }

    if (data.explanation) {
        const exp = data.explanation;
        html += `
            <div class="explain-card">
                <div class="explain-title">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
                    Explainable AI (Синтаксический разбор):
                </div>
                <div class="explain-grid">
                    <div class="explain-item"><strong>Таблицы:</strong> ${escapeHtml((exp.tables || []).join(', ') || '—')}</div>
                    <div class="explain-item"><strong>Связи JOIN:</strong> ${escapeHtml((exp.joins || []).join('; ') || '—')}</div>
                    <div class="explain-item"><strong>Фильтры WHERE:</strong> ${escapeHtml((exp.filters || []).join('; ') || '—')}</div>
                    <div class="explain-item"><strong>Агрегации:</strong> ${escapeHtml((exp.aggregations || []).join('; ') || '—')}</div>
                </div>
            </div>
        `;
    }

    if (data.sql && data.sql !== '—') {
        html += `
            <div class="sql-card">
                <div class="sql-card-header">
                    <span>Сгенерированный SQL (PostgreSQL AST)</span>
                    <button class="btn-copy-sql" onclick="copySql(this)">Копировать</button>
                </div>
                <div class="sql-code">${escapeHtml(data.sql)}</div>
            </div>
        `;
    }

    if (data.columns && data.data) {
        if (data.data.length === 0) {
            html += '<p style="color: #64748b; font-style: italic; margin-top: 10px;">Записей по заданному критерию не обнаружено.</p>';
        } else {
            html += '<div class="table-container"><table class="data-table"><thead><tr>';
            data.columns.forEach(col => {
                html += `<th>${escapeHtml(col)}</th>`;
            });
            html += '</tr></thead><tbody>';

            data.data.forEach(row => {
                html += '<tr>';
                data.columns.forEach(col => {
                    const val = row[col];
                    html += `<td>${escapeHtml(val !== null && val !== undefined ? val : '—')}</td>`;
                });
                html += '</tr>';
            });
            html += '</tbody></table></div>';
            html += `
                <div class="table-footer">
                    <span>Транзакция выполнена успешно</span>
                    <span>Всего строк: <b>${data.count}</b></span>
                </div>
            `;
        }
    }

    appendBotHtml(html);
}