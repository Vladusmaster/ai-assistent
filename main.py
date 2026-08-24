from fastapi import FastAPI
from pydantic import BaseModel

# Создаем приложение бэкенда
app = FastAPI()

# Структура входящего JSON-запроса
class UserQuery(BaseModel):
    text: str

# Эндпоинт, который будет принимать запросы от html-страницы
@app.post("/api/ask")
def ask_database(query: UserQuery):
    # Пока нейросеть не подключена, просто возвращаем текст обратно
    return {"status": "success", "reply": f"Сервер получил вопрос: {query.text}"}