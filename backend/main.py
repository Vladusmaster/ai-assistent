import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # <-- Добавили этот импорт
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

class UserRequest(BaseModel):
    question: str

@app.post("/api/ask")
async def ask_agent(request: UserRequest):
    if not GIGACHAT_CREDENTIALS:
        raise HTTPException(status_code=500, detail="Ключ GigaChat не найден в .env")

    
    auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    
    headers = {
        "Authorization": f"Bearer {GIGACHAT_CREDENTIALS}",
        "RqUID": "твой-уникальный-идентификатор-запроса", # Генерируется через uuid
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            
            mock_sql_from_llm = f"SELECT * FROM students LIMIT 5;"
            
            return {
                "status": "success",
                "original_question": request.question,
                "generated_sql": mock_sql_from_llm,
                "message": "Агент подключен (заглушка)"
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))