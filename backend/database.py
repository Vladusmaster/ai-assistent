import os
import asyncpg
from typing import Any, Dict, List, Tuple
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "185.241.193.203").strip()
DB_PORT = int(os.getenv("DB_PORT", "5432").strip())
DB_NAME = os.getenv("DB_NAME", "vesna-db5").strip()
DB_USER = os.getenv("DB_USER", "vdb5_user").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "X59b39C9-5D4X4NHn").strip()

pool: asyncpg.Pool = None

async def init_db_pool():
    global pool
    pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        min_size=2,
        max_size=10
    )

async def close_db_pool():
    global pool
    if pool:
        await pool.close()

async def execute_safe_query(sql_query: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    if not pool:
        raise RuntimeError("Пул соединений с БД не инициализирован.")
        
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL statement_timeout = '3000ms';")
            records = await conn.fetch(sql_query)
            
            if not records:
                return [], []
                
            columns = list(records[0].keys())
            rows = [dict(record) for record in records]
            return columns, rows