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

from database import init_db_pool, close_db_pool, execute_safe_query
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

@app.post("/api/ask")
async def ask_question(req: QueryRequest):
    logging.info(f"Получен вопрос пользователя: {req.question}")
    
    try:
        llm_response = await generate_sql_and_explanation(req.question)
        raw_sql = llm_response.get("sql", "")
        explanation = llm_response.get("explanation", {})
        summary_ru = llm_response.get("summary_ru", "")
        
        safe_sql = validate_and_sanitize_sql(raw_sql)
        columns, rows = await execute_safe_query(safe_sql)
        
        return {
            "status": "success",
            "sql": safe_sql,
            "explanation": explanation,
            "summary": summary_ru,
            "columns": columns,
            "data": rows,
            "count": len(rows)
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