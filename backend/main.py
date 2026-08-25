import os
import httpx
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

app = FastAPI()

# Настройка CORS для связи с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str

# Ключи Yandex
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

# Подключение к БД
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = os.getenv("DB_NAME", "vesna-db5")
DB_HOST = os.getenv("DB_HOST", "db")

# White-list разрешенных таблиц
ALLOWED_TABLES = ["students", "enrollments", "courses", "grades", "departments", "teachers"]

@app.post("/api/ask")
async def ask_database(request: QueryRequest):
    # 1. Запрос к YandexGPT для генерации SQL
    prompt = f"Напиши только SQL запрос для PostgreSQL к базе данных. Вопрос: {request.question}. Верни только код без пояснений."
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID
    }
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {"stream": False, "temperature": 0.1, "maxTokens": "1000"},
        "messages": [{"role": "user", "text": prompt}]
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post("https://llm.api.cloud.yandex.net/foundationModels/v1/completion", headers=headers, json=payload)
            if resp.status_code != 200:
                print("ОШИБКА ЯНДЕКСА:", resp.status_code, resp.text)
                raise HTTPException(status_code=500, detail="Ошибка сервиса YandexGPT")
            
            data = resp.json()
            sql_query = data['result']['alternatives'][0]['message']['text']
            
            # Очистка форматирования Markdown
            sql_query = sql_query.strip('```sql').strip('```').strip()
            
        except Exception as e:
            print("ИСКЛЮЧЕНИЕ ПРИ ОБРАЩЕНИИ К LLM:", str(e))
            raise HTTPException(status_code=500, detail=f"Ошибка запроса к YandexGPT: {str(e)}")

    # 2. Слой валидации и безопасности
    sql_upper = sql_query.upper()
    
    # 2.1 Разрешаем только чтение (SELECT)
    if not sql_upper.startswith("SELECT"):
        return {"status": "error", "message": "В целях безопасности разрешены только SELECT запросы.", "generated_sql": sql_query}
    
    # 2.2 Проверка по whitelist
    if not any(table.upper() in sql_upper for table in ALLOWED_TABLES):
        return {"status": "error", "message": "Запрос к неразрешенной таблице.", "generated_sql": sql_query}

    # 2.3 Автоматический LIMIT
    sql_query = sql_query.strip().rstrip(";")
    if "LIMIT" not in sql_upper:
        sql_query += " LIMIT 50"

    # 3. Выполнение запроса в PostgreSQL
    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, connect_timeout=5)
        cursor = conn.cursor()
        
        cursor.execute("SET statement_timeout = '5s'")
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        cursor.close()
        conn.close()
        
        return {"status": "success", "generated_sql": sql_query, "columns": columns, "rows": rows}
        
    except Exception as e:
        return {"status": "error", "message": str(e), "generated_sql": sql_query}