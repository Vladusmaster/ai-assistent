# AI-ассистент базы данных РЭУ им. Г. В. Плеханова

Интеллектуальный ассистент для безопасного анализа данных PostgreSQL на естественном языке с поддержкой Explainable AI и адаптивным контролем объема выборки.

## Основной стек
- **Backend:** Python 3.11, FastAPI, asyncpg, sqlparse, httpx, Pydantic
- **LLM:** Yandex Foundation Models (YandexGPT)
- **Database:** PostgreSQL
- **Frontend:** HTML5, CSS3, Vanilla JS (встраиваемый виджет)
- **DevOps:** Docker, Docker Compose

---

## Настройка переменных окружения

Создайте файл `.env` в корневом каталоге проекта:

```dotenv
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=

YANDEX_API_KEY=ваш_секретный_api_key
YANDEX_FOLDER_ID=ваш_folder_id

## Инструкция по запуску
1. Клонировать репозиторий:
   ```bash
   git clone [https://github.com/Vladusmaster/ai-assistent.git](https://github.com/Vladusmaster/ai-assistent.git)
   cd ai-assistent
   code .
