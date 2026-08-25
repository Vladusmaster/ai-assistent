# AI-ассистент для анализа данных университета (Код Байкала 2026)

Интеллектуальный коннектор для безопасного анализа данных PostgreSQL с использованием LLM (Text-to-SQL).

## Стек технологий
* **Backend:** Python 3.10+, FastAPI, Uvicorn
* **Database Driver:** psycopg2-binary
* **Frontend:** HTML5, CSS3, JavaScript (Fetch API)
* **LLM Integration:** GigaChat API (Сбер)
* **Containerization:** Docker, Docker Compose

## Архитектура безопасности
* Поддержка только `SELECT`-запросов.
* Whitelist разрешенных таблиц.
* Автоматическое ограничение `LIMIT`.
* Ограничение времени выполнения (`statement_timeout`).
* Обезличивание и защита персональных данных студентов.

## Инструкция по запуску
1. Клонировать репозиторий:
   ```bash
   git clone [https://github.com/Vladusmaster/ai-assistent.git](https://github.com/Vladusmaster/ai-assistent.git)
   cd ai-assistent