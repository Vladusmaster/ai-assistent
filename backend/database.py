import os
import asyncpg
from typing import Any, Dict, List, Tuple, Optional
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "185.241.193.203").strip()
DB_PORT = int(os.getenv("DB_PORT", "5432").strip())
DB_NAME = os.getenv("DB_NAME", "vesna-db5").strip()
DB_USER = os.getenv("DB_USER", "vdb5_user").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "X59b39C9-5D4X4NHn").strip()

_pool: Optional[asyncpg.Pool] = None

async def init_db_pool():
    global _pool
    _pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        min_size=2,
        max_size=10
    )

async def close_db_pool():
    global _pool
    if _pool:
        await _pool.close()

def get_db_pool() -> asyncpg.Pool:
    if not _pool:
        raise RuntimeError("Пул соединений с БД не инициализирован.")
    return _pool

async def create_log_table():
    pool = get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id SERIAL PRIMARY KEY,
                user_question TEXT NOT NULL,
                generated_sql TEXT,
                execution_time_ms DOUBLE PRECISION NOT NULL,
                status VARCHAR(50) NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

async def log_user_query(question: str, sql: str | None, time_ms: float, status: str, error: str | None = None):
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO query_logs (user_question, generated_sql, execution_time_ms, status, error_message)
                   VALUES ($1, $2, $3, $4, $5)""",
                question, sql, time_ms, status, error
            )
    except Exception as e:
        print(f"Ошибка записи лога: {e}")

async def execute_safe_query(sql_query: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    pool = get_db_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL statement_timeout = '3000ms';")
            records = await conn.fetch(sql_query)
            
            if not records:
                return [], []
                
            columns = list(records[0].keys())
            rows = [dict(record) for record in records]
            return columns, rows