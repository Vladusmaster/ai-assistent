import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "185.241.193.203"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "vesna-db5"),
        user=os.getenv("DB_USER", "vdb5_user"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """)
    rows = cur.fetchall()
    print("\n--- ТАБЛИЦЫ В БАЗЕ ---")
    for row in rows:
        print(row)
    conn.close()
except Exception as e:
    print(f"\nОшибка: {e}")
