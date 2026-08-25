<<<<<<< HEAD
FROM python:3.11-slim
=======
FROM cr.yandex/mirror/python:3.11-slim
>>>>>>> e733783 (обновил бд)

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
<<<<<<< HEAD
    build-essential \
=======
    gcc \
    libpq-dev \
>>>>>>> e733783 (обновил бд)
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

<<<<<<< HEAD
# Копируем бэкенд и фронтенд
=======
>>>>>>> e733783 (обновил бд)
COPY backend/ ./backend/
COPY frontend/ ./frontend/

EXPOSE 8000

<<<<<<< HEAD
# Запуск приложения
=======
>>>>>>> e733783 (обновил бд)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]