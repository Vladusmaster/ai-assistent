import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database import init_db_pool, close_db_pool, execute_safe_query, pool
from security import validate_and_sanitize_sql, SecurityError
from llm import generate_sql_and_explanation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_pool()
    logging.info("Подключение к PostgreSQL успешно установлено.")
    yield
    await close_db_pool()
    logging.info("Подключение к PostgreSQL закрыто.")

app = FastAPI(title="AI DB Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str

async def analyze_query_volume(base_sql: str) -> tuple[int, str | None, list[str]]:
    clean_sql = base_sql.split(" LIMIT ")[0].rstrip(";")
    count_sql = f"SELECT COUNT(*) AS total FROM ({clean_sql}) AS subquery_count"
    
    warning = None
    suggested_filters = []
    
    try:
        async with pool.acquire() as conn:
            total_records = await conn.fetchval(count_sql)
            
            if total_records > 50:
                warning = f"Широкий запрос: найдено {total_records} записей. Применен автоматический LIMIT."
                if "заявления" in clean_sql or "applications" in clean_sql:
                    suggested_filters = [
                        'Указать год ("год_кампании" = 2026)',
                        'Выбрать статус ("статус" = \'Зачислен\')',
                        'Фильтр по форме ("основание_поступления" = \'Бюджетные места\')'
                    ]
                elif "студенты" in clean_sql or "students" in clean_sql:
                    suggested_filters = [
                        'Фильтр по курсу ("курс" = 1)',
                        'Фильтр по группе ("учебная_группа" = \'ПИ-231\')',
                        'Фильтр по статусу ("статус_студента" = \'Обучается\')'
                    ]
                elif "оценки" in clean_sql or "grades" in clean_sql:
                    suggested_filters = [
                        'Указать семестр ("семестр" = 2)',
                        'Только задолженности ("академическая_задолженность" = true)'
                    ]
                else:
                    suggested_filters = ["Уточните факультет или кафедру", "Добавьте временной интервал"]
                    
            return total_records, warning, suggested_filters
    except Exception:
        return 0, None, []

@app.post("/api/ask")
async def ask_question(req: QueryRequest):
    logging.info(f"Получен вопрос пользователя: {req.question}")
    
    try:
        llm_response = await generate_sql_and_explanation(req.question)
        raw_sql = llm_response.get("sql")
        explanation = llm_response.get("explanation", {})
        summary_ru = llm_response.get("summary_ru", "")
        
        if not raw_sql:
            return {
                "status": "success",
                "sql": None,
                "explanation": None,
                "summary": summary_ru or "Запрос не относится к данным реестров университета. Задайте вопрос по кафедрам, преподавателям, студентам или абитуриентам.",
                "columns": [],
                "data": [],
                "count": 0,
                "total_available": 0,
                "warning": None,
                "suggested_filters": []
            }
        
        safe_sql = validate_and_sanitize_sql(raw_sql, default_limit=100)
        total_found, warning, suggested_filters = await analyze_query_volume(safe_sql)
        
        columns, rows = await execute_safe_query(safe_sql)
        
        return {
            "status": "success",
            "sql": safe_sql,
            "explanation": explanation,
            "summary": summary_ru,
            "columns": columns,
            "data": rows,
            "count": len(rows),
            "total_available": total_found,
            "warning": warning,
            "suggested_filters": suggested_filters
        }
        
    except SecurityError as se:
        logging.warning(f"Ошибка безопасности: {str(se)}")
        return {
            "status": "error",
            "type": "security_violation",
            "message": str(se)
        }
    except Exception as e:
        logging.error(f"Системная ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")