const chatHistory = document.getElementById('chatHistory');
const userInput = document.getElementById('userInput');
const loader = document.getElementById('loader');

const tableStates = new Map();
const PAGE_SIZE = 8;

function handleKeyPress(event) {
    if (event.key === 'Enter') sendMessage();
}

function applyFilter(filterText) {
    userInput.value = userInput.value ? `${userInput.value} (${filterText})` : filterText;
    userInput.focus();
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

            if (data.warning) {
                let chipsHtml = '';
                if (data.suggested_filters && data.suggested_filters.length > 0) {
                    chipsHtml = `<div class="filter-chips">` +
                        data.suggested_filters.map(f => `<span class="chip" onclick="applyFilter('${f}')">+ ${f}</span>`).join('') +
                        `</div>`;
                }
                botReply += `
                    <div class="warning-box">
                        <b>⚠️ Внимание:</b> ${data.warning}
                        ${chipsHtml}
                    </div>
                `;
            }

            if (data.columns && data.data) {
                if (data.data.length === 0) {
                    botReply += '<p style="margin-top: 10px;"><i>Данных по заданному условию не найдено.</i></p>';
                } else {
                    const tableId = 'tbl_' + Math.random().toString(36).substring(2, 9);
                    tableStates.set(tableId, {
                        columns: data.columns,
                        rows: data.data,
                        currentPage: 1,
                        totalPages: Math.ceil(data.data.length / PAGE_SIZE)
                    });

                    botReply += `
                        <div class="table-wrap" id="wrap_${tableId}">
                            ${renderTableHtml(tableId, 1)}
                        </div>
                        <div class="pagination-controls" id="ctrl_${tableId}">
                            ${renderPaginationControls(tableId, 1)}
                        </div>
                    `;
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

function renderTableHtml(tableId, page) {
    const state = tableStates.get(tableId);
    const start = (page - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    const pageRows = state.rows.slice(start, end);

    let html = `<table><thead><tr>`;
    state.columns.forEach(col => { html += `<th>${col}</th>`; });
    html += `</tr></thead><tbody>`;

    pageRows.forEach(row => {
        html += `<tr>`;
        state.columns.forEach(col => {
            const val = row[col];
            html += `<td>${val !== null && val !== undefined ? val : ''}</td>`;
        });
        html += `</tr>`;
    });
    html += `</tbody></table>`;
    return html;
}

function renderPaginationControls(tableId, page) {
    const state = tableStates.get(tableId);
    return `
        <span>Строк: ${state.rows.length} | Стр. ${page} из ${state.totalPages}</span>
        <div>
            <button class="pagination-btn" onclick="changePage('${tableId}', -1)" ${page === 1 ? 'disabled' : ''}>← Назад</button>
            <button class="pagination-btn" onclick="changePage('${tableId}', 1)" ${page === state.totalPages ? 'disabled' : ''}>Вперед →</button>
        </div>
    `;
}

function changePage(tableId, delta) {
    const state = tableStates.get(tableId);
    const newPage = state.currentPage + delta;
    if (newPage < 1 || newPage > state.totalPages) return;

    state.currentPage = newPage;
    document.getElementById(`wrap_${tableId}`).innerHTML = renderTableHtml(tableId, newPage);
    document.getElementById(`ctrl_${tableId}`).innerHTML = renderPaginationControls(tableId, newPage);
}

function addMessage(htmlContent, className) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${className}`;
    msgDiv.innerHTML = htmlContent;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight; 
}