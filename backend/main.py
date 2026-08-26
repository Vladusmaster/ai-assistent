import time
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

from database import init_db_pool, close_db_pool, execute_safe_query, create_log_table, log_user_query, pool
from security import validate_and_sanitize_sql, SecurityError
from llm import generate_sql_and_explanation, ask_yandex_gpt_analytics

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_pool()
    await create_log_table()
    logging.info("Подключение к PostgreSQL и таблица логов готовы.")
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
    start_time = time.perf_counter()
    logging.info(f"Получен вопрос: {req.question}")
    
    try:
        llm_response = await generate_sql_and_explanation(req.question)
        raw_sql = llm_response.get("sql", "")
        explanation = llm_response.get("explanation", {})
        summary_ru = llm_response.get("summary_ru", "")
        
        safe_sql = validate_and_sanitize_sql(raw_sql, default_limit=100)
        columns, rows = await execute_safe_query(safe_sql)
        
        execution_time = (time.perf_counter() - start_time) * 1000
        await log_user_query(req.question, safe_sql, execution_time, "SUCCESS")
        
        return {
            "status": "success",
            "sql": safe_sql,
            "explanation": explanation,
            "summary": summary_ru,
            "columns": columns,
            "data": rows,
            "count": len(rows),
            "execution_time_ms": round(execution_time, 2)
        }
        
    except SecurityError as se:
        execution_time = (time.perf_counter() - start_time) * 1000
        await log_user_query(req.question, None, execution_time, "SECURITY_BLOCKED", str(se))
        return {
            "status": "error",
            "type": "security_violation",
            "message": str(se)
        }
    except Exception as e:
        execution_time = (time.perf_counter() - start_time) * 1000
        await log_user_query(req.question, None, execution_time, "ERROR", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics")
async def get_analytics():
    async with pool.acquire() as conn:
        records = await conn.fetch("SELECT user_question, status, execution_time_ms FROM query_logs ORDER BY id DESC LIMIT 50")
        total_queries = await conn.fetchval("SELECT count(*) FROM query_logs")
        avg_time = await conn.fetchval("SELECT AVG(execution_time_ms) FROM query_logs WHERE status = 'SUCCESS'")
        
    log_texts = [f"- Вопрос: {r['user_question']} | Статус: {r['status']}" for r in records]
    ai_summary = await ask_yandex_gpt_analytics("\n".join(log_texts))
    
    return {
        "total_queries": total_queries or 0,
        "avg_execution_time_ms": round(avg_time or 0, 2),
        "ai_insights": ai_summary,
        "recent_logs": [dict(r) for r in records[:10]]
    }

frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")