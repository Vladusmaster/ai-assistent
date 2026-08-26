import time
import os
import sys
import logging
from contextlib import asynccontextmanager
import asyncpg
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database import (
    init_db_pool,
    close_db_pool,
    get_db_pool,
    execute_safe_query,
    create_log_table,
    log_user_query,
    verify_password
)
from security import (
    check_prompt_security_intent,
    validate_and_sanitize_sql,
    SecurityViolationError,
    UnrecognizedQueryError
)
from llm import generate_sql_and_explanation, fix_sql_with_error, ask_yandex_gpt_analytics

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

class LoginRequest(BaseModel):
    username: str
    password: str

class QueryRequest(BaseModel):
    question: str
    role: str = "applicant"

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    pool = get_db_pool()
    async with pool.acquire() as conn:
        user_row = await conn.fetchrow(
            "SELECT username, password_hash, role, full_name, email FROM users WHERE username = $1",
            req.username.strip()
        )
        
    if not user_row or not verify_password(user_row["password_hash"], req.password.strip()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль."
        )
        
    return {
        "status": "success",
        "user": {
            "username": user_row["username"],
            "role": user_row["role"],
            "full_name": user_row["full_name"],
            "email": user_row["email"]
        }
    }

async def analyze_query_volume(base_sql: str) -> tuple[int, str | None, list[str]]:
    if not base_sql or base_sql == "—":
        return 0, None, []
        
    clean_sql = base_sql.split(" LIMIT ")[0].rstrip(";")
    count_sql = f"SELECT COUNT(*) AS total FROM ({clean_sql}) AS subquery_count"
    
    warning = None
    suggested_filters = []
    
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            total_records = await conn.fetchval(count_sql)
            
            if total_records and total_records > 10:
                warning = f"Широкая выборка: найдено {total_records} записей. Применена пагинация."
                if "applications" in clean_sql:
                    suggested_filters = [
                        "Покажи заявления за 2026 год",
                        "Покажи только зачисленных абитуриентов",
                        "Покажи очную форму обучения"
                    ]
                elif "students" in clean_sql:
                    suggested_filters = [
                        "Покажи студентов 2 курса",
                        "Покажи студентов группы ПИ",
                        "Покажи обучающихся студентов"
                    ]
                elif "grades" in clean_sql:
                    suggested_filters = [
                        "Покажи оценки за 2 семестр",
                        "Покажи только с задолженностями"
                    ]
                else:
                    suggested_filters = [
                        "Покажи кафедры IT",
                        "Покажи аудитории 1 корпуса"
                    ]
                    
            return total_records or 0, warning, suggested_filters
    except Exception:
        return 0, None, []

@app.post("/api/ask")
async def ask_question(req: QueryRequest):
    start_time = time.perf_counter()
    logging.info(f"Получен вопрос ({req.role}): {req.question}")
    
    try:
        check_prompt_security_intent(req.question)

        llm_response = await generate_sql_and_explanation(req.question, role=req.role)
        raw_sql = llm_response.get("sql", "").strip()
        explanation = llm_response.get("explanation", {})
        summary_ru = llm_response.get("summary_ru", "")
        
        if not raw_sql:
            execution_time = (time.perf_counter() - start_time) * 1000
            await log_user_query(req.question, None, execution_time, "UNRECOGNIZED_PROMPT")
            return {
                "status": "info",
                "type": "unrecognized_query",
                "message": summary_ru or "Запрос не распознан. Пожалуйста, сформулируйте вопрос о данных университета."
            }
        
        safe_sql = validate_and_sanitize_sql(raw_sql, role=req.role, default_limit=100)
        
        try:
            columns, rows = await execute_safe_query(safe_sql)
        except asyncpg.PostgresError as pe:
            logging.warning(f"Ошибка выполнения SQL ({pe.message}). Запуск Self-Correction...")
            fixed_response = await fix_sql_with_error(req.question, safe_sql, pe.message, role=req.role)
            raw_sql = fixed_response.get("sql", "").strip()
            
            if not raw_sql:
                return {
                    "status": "info",
                    "type": "unrecognized_query",
                    "message": "Не удалось составить запрос к базе данных. Уточните формулировку вопроса."
                }
                
            explanation = fixed_response.get("explanation", {})
            summary_ru = fixed_response.get("summary_ru", "")
            safe_sql = validate_and_sanitize_sql(raw_sql, role=req.role, default_limit=100)
            columns, rows = await execute_safe_query(safe_sql)
            
        total_found, warning, suggested_filters = await analyze_query_volume(safe_sql)
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
            "total_available": total_found,
            "warning": warning,
            "suggested_filters": suggested_filters,
            "execution_time_ms": round(execution_time, 2)
        }
        
    except SecurityViolationError as sve:
        execution_time = (time.perf_counter() - start_time) * 1000
        await log_user_query(req.question, None, execution_time, "SECURITY_BLOCKED", str(sve))
        return {
            "status": "error",
            "type": "security_violation",
            "message": str(sve)
        }
    except UnrecognizedQueryError as uqe:
        execution_time = (time.perf_counter() - start_time) * 1000
        await log_user_query(req.question, None, execution_time, "UNRECOGNIZED_QUERY", str(uqe))
        return {
            "status": "info",
            "type": "unrecognized_query",
            "message": "По данному запросу не удалось сопоставить сущности. Уточните вопрос."
        }
    except asyncpg.PostgresError as pe:
        execution_time = (time.perf_counter() - start_time) * 1000
        await log_user_query(req.question, raw_sql if 'raw_sql' in locals() else None, execution_time, "DB_ERROR", str(pe))
        return {
            "status": "error",
            "type": "db_error",
            "message": f"Ошибка выполнения запроса в СУБД: {pe.message}."
        }
    except Exception as e:
        execution_time = (time.perf_counter() - start_time) * 1000
        await log_user_query(req.question, None, execution_time, "SYSTEM_ERROR", str(e))
        return {
            "status": "error",
            "type": "system_error",
            "message": f"Ошибка обработки: {str(e)}"
        }

@app.get("/api/analytics")
async def get_analytics():
    try:
        pool = get_db_pool()
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
    except Exception as e:
        return {
            "total_queries": 0,
            "avg_execution_time_ms": 0,
            "ai_insights": f"Ошибка сбора аналитики: {str(e)}",
            "recent_logs": []
        }

frontend_dir = os.path.join(PROJECT_ROOT, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")