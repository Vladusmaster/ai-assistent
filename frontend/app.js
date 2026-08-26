const chatOverlay = document.getElementById('chatOverlay');
const chatHistory = document.getElementById('chatHistory');
const userInput = document.getElementById('userInput');
const loader = document.getElementById('loader');
const sendBtn = document.getElementById('sendBtn');
const userRoleSelect = document.getElementById('userRoleSelect');
const loginOverlay = document.getElementById('loginOverlay');
const loginBtnTrigger = document.getElementById('loginBtnTrigger');
const userProfileBadge = document.getElementById('userProfileBadge');
const headerUserName = document.getElementById('headerUserName');
const headerUserRole = document.getElementById('headerUserRole');
const userAvatarLetter = document.getElementById('userAvatarLetter');
const loginError = document.getElementById('loginError');

window.tableStorage = window.tableStorage || new Map();
const PAGE_SIZE = 10;

const ROLE_NAMES = {
    'admin': 'Деканат / Администрация',
    'teacher': 'Преподаватель',
    'student': 'Студент',
    'applicant': 'Абитуриент'
};

document.addEventListener('DOMContentLoaded', () => {
    restoreUserSession();
});

function restoreUserSession() {
    const raw = localStorage.getItem('reu_user');
    if (raw) {
        try {
            const user = JSON.parse(raw);
            applyUserToUI(user);
        } catch (e) {
            localStorage.removeItem('reu_user');
        }
    }
}

function applyUserToUI(user) {
    if (userRoleSelect) {
        userRoleSelect.value = user.role;
        userRoleSelect.disabled = true;
        userRoleSelect.title = "Роль зафиксирована текущей учетной записью";
    }
    if (loginBtnTrigger) loginBtnTrigger.style.display = 'none';
    if (userProfileBadge) {
        userProfileBadge.style.display = 'flex';
        headerUserName.innerText = user.full_name.split(' ')[0] || user.username;
        headerUserRole.innerText = ROLE_NAMES[user.role] || user.role;
        userAvatarLetter.innerText = (user.full_name || user.username).charAt(0).toUpperCase();
    }
}

function openLoginModal() {
    loginError.innerText = '';
    loginOverlay.style.display = 'flex';
    document.getElementById('loginUsername').focus();
}

function closeLoginModal() {
    loginOverlay.style.display = 'none';
}

function handleLoginOverlayClick(event) {
    if (event.target === loginOverlay) {
        closeLoginModal();
    }
}

function fillDemo(u, p) {
    document.getElementById('loginUsername').value = u;
    document.getElementById('loginPassword').value = p;
}

async function submitLoginForm(e) {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    const btn = document.getElementById('loginSubmitBtn');

    if (!username || !password) return;

    btn.disabled = true;
    loginError.innerText = '';

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || 'Неверный логин или пароль');
        }

        localStorage.setItem('reu_user', JSON.stringify(data.user));
        applyUserToUI(data.user);
        closeLoginModal();

        appendBotHtml(`
            <div class="warning-banner" style="background: #f0fdf4; border-color: #bbf7d0; border-left-color: #17d97b;">
                <div class="warning-header" style="color: #166534;">✅ Успешная авторизация:</div>
                <div style="font-size: 13px; color: #14532d;">Здравствуйте, <b>${escapeHtml(data.user.full_name)}</b>! Вам присвоен уровень доступа: <b>${ROLE_NAMES[data.user.role]}</b> (переключатель зафиксирован).</div>
            </div>
        `);

    } catch (err) {
        loginError.innerText = err.message;
    } finally {
        btn.disabled = false;
    }
}

function logoutUser() {
    localStorage.removeItem('reu_user');
    if (userProfileBadge) userProfileBadge.style.display = 'none';
    if (loginBtnTrigger) loginBtnTrigger.style.display = 'inline-flex';
    if (userRoleSelect) {
        userRoleSelect.value = 'applicant';
        userRoleSelect.disabled = false;
        userRoleSelect.title = "Выберите роль вручную (гостевой режим)";
    }
    
    appendBotHtml(`
        <div class="warning-banner" style="background: #eff6ff; border-color: #bfdbfe; border-left-color: #3b82f6;">
            <div class="warning-header" style="color: #1e40af;">ℹ️ Вы вышли из профиля:</div>
            <div style="font-size: 13px; color: #1e3a8a;">Уровень доступа сброшен до базового. Ручной выбор роли разблокирован.</div>
        </div>
    `);
}

function getSelectedRole() {
    const savedUser = localStorage.getItem('reu_user');
    if (savedUser) {
        try {
            return JSON.parse(savedUser).role;
        } catch (e) {}
    }
    return userRoleSelect ? userRoleSelect.value : 'applicant';
}

function onRoleChange() {
    const roleName = userRoleSelect.options[userRoleSelect.selectedIndex].text;
    appendBotHtml(`
        <div class="warning-banner" style="background: #f0fdf4; border-color: #bbf7d0; border-left-color: #17d97b;">
            <div class="warning-header" style="color: #166534;">🔄 Режим доступа изменен:</div>
            <div style="font-size: 13px; color: #14532d;">Вы переключились на роль <b>${escapeHtml(roleName)}</b>. Политики фильтрации и видимости ПДн обновлены.</div>
        </div>
    `);
}

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
                Чат очищен. Задайте новый вопрос к базе данных РЭУ им. Г.В. Плеханова.
            </div>
        </div>
    `;
    window.tableStorage.clear();
}

function quickSend(promptText) {
    userInput.value = promptText;
    sendMessage();
}

function applyFilterBtn(btn) {
    const query = btn.getAttribute('data-query');
    if (query) {
        userInput.value = query;
        sendMessage();
    }
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

function renderTableRows(tableId, page) {
    const state = window.tableStorage.get(tableId);
    if (!state) return '';

    const start = (page - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    const pageRows = state.rows.slice(start, end);

    let html = `<table class="data-table"><thead><tr>`;
    state.columns.forEach(col => {
        html += `<th>${escapeHtml(col)}</th>`;
    });
    html += `</tr></thead><tbody>`;

    pageRows.forEach(row => {
        html += `<tr>`;
        state.columns.forEach(col => {
            const val = row[col];
            html += `<td>${escapeHtml(val !== null && val !== undefined ? val : '—')}</td>`;
        });
        html += `</tr>`;
    });
    html += `</tbody></table>`;
    return html;
}

function renderPaginationBar(tableId, page) {
    const state = window.tableStorage.get(tableId);
    if (!state) return '';

    const totalPages = state.totalPages;
    const totalCount = state.rows.length;
    const startIdx = (page - 1) * PAGE_SIZE + 1;
    const endIdx = Math.min(page * PAGE_SIZE, totalCount);

    return `
        <div class="pagination-info">
            Показаны <b>${startIdx}–${endIdx}</b> из <b>${totalCount}</b> (Стр. <b>${page}</b>/<b>${totalPages}</b>)
        </div>
        <div class="pagination-actions">
            <button class="btn-page" onclick="changePage('${tableId}', -1)" ${page <= 1 ? 'disabled' : ''}>
                ← Назад
            </button>
            <button class="btn-page" onclick="changePage('${tableId}', 1)" ${page >= totalPages ? 'disabled' : ''}>
                Вперед →
            </button>
        </div>
    `;
}

window.changePage = function(tableId, delta) {
    const state = window.tableStorage.get(tableId);
    if (!state) return;

    const newPage = state.currentPage + delta;
    if (newPage < 1 || newPage > state.totalPages) return;

    state.currentPage = newPage;

    const wrapEl = document.getElementById(`wrap_${tableId}`);
    const ctrlEl = document.getElementById(`ctrl_${tableId}`);

    if (wrapEl) wrapEl.innerHTML = renderTableRows(tableId, newPage);
    if (ctrlEl) ctrlEl.innerHTML = renderPaginationBar(tableId, newPage);
};

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
            body: JSON.stringify({
                question: text,
                role: getSelectedRole()
            })
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
    if (data.status === 'info' || data.type === 'unrecognized_query') {
        appendBotHtml(`
            <div class="warning-banner" style="background: #eff6ff; border-color: #bfdbfe; border-left-color: #3b82f6;">
                <div class="warning-header" style="color: #1e40af;">ℹ️ Обратите внимание:</div>
                <div style="font-size: 13.5px; color: #1e3a8a;">${escapeHtml(data.message || data.summary)}</div>
            </div>
        `);
        return;
    }

    if (data.status === 'error') {
        const errorTitle = data.type === 'security_violation'
            ? 'Отклонено системой безопасности'
            : (data.type === 'db_error' ? 'Ошибка структуры запроса к БД' : 'Сбой обработки');

        appendBotHtml(`
            <div class="error-card">
                ⚠️ <b>${escapeHtml(errorTitle)}:</b> ${escapeHtml(data.message)}
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

    if (data.warning) {
        let chipsHtml = '';
        if (data.suggested_filters && data.suggested_filters.length > 0) {
            chipsHtml = `<div class="filter-chips">` +
                data.suggested_filters.map(f => {
                    return `<span class="chip-filter" data-query="${escapeHtml(f)}" onclick="applyFilterBtn(this)">+ ${escapeHtml(f)}</span>`;
                }).join('') +
                `</div>`;
        }
        html += `
            <div class="warning-banner">
                <div class="warning-header">⚠️ ${escapeHtml(data.warning)}</div>
                ${chipsHtml}
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

    if (data.data) {
        if (data.data.length === 0) {
            html += '<p style="color: #64748b; font-style: italic; margin-top: 10px;">Записей по заданному критерию не обнаружено.</p>';
        } else if (data.columns && data.columns.length > 0) {
            const tableId = 'tbl_' + Math.random().toString(36).substring(2, 9);
            const totalPages = Math.max(1, Math.ceil(data.data.length / PAGE_SIZE));

            window.tableStorage.set(tableId, {
                columns: data.columns,
                rows: data.data,
                currentPage: 1,
                totalPages: totalPages
            });

            html += `
                <div class="table-container" id="wrap_${tableId}">
                    ${renderTableRows(tableId, 1)}
                </div>
                <div class="pagination-bar" id="ctrl_${tableId}">
                    ${renderPaginationBar(tableId, 1)}
                </div>
                <div class="table-footer">
                    <span>Транзакция выполнена успешно</span>
                    <span>Всего строк в выборке: <b>${data.count}</b></span>
                </div>
            `;
        }
    }

    appendBotHtml(html);
}