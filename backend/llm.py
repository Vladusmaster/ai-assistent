import json
import os
import re
import httpx
from typing import Any, Dict
from dotenv import load_dotenv

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "").strip()
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "").strip()
YANDEX_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

SYSTEM_PROMPT = """
Ты — AI-ассистент базы данных PostgreSQL РЭУ им. Г. В. Плеханова.
Твоя задача: преобразовывать запросы пользователя на естественном языке в валидный SQL-запрос (PostgreSQL dialect) и формировать блок Explainable AI.

СХЕМА БАЗЫ ДАННЫХ:
1. faculties (id, name, short_name, dean_full_name, building, contact_email)
2. departments (id, faculty_id, name, head_full_name)
3. teachers (id, department_id, full_name, academic_degree, academic_title, position, email)
4. programs (id, faculty_id, code, name, degree_level, budget_places, paid_places, tuition_fee_per_year)
5. applications (id, program_id, application_number, year, math_score, russian_score, special_score, total_score, education_form, education_basis, status, submission_date)
6. students (id, program_id, student_ticket_number, study_group, course_year, enrollment_year, education_basis, status)
7. classrooms (id, building, room_number, capacity, room_type)
8. courses (id, department_id, teacher_id, name, semester, total_hours, control_type)
9. grades (id, student_id, course_id, semester, grade_points, letter_grade, is_debt, exam_date)
10. classroom_schedules (id, classroom_id, course_id, day_of_week, time_slot, study_group, attendees_count)

ПРАВИЛА БЕЗОПАСНОСТИ:
1. Разрешены только SELECT-запросы. Запрещены любые изменения данных.
2. Персональные данные студентов и абитуриентов выводятся строго в агрегированном/обезличенном виде (COUNT, AVG, группировки).
3. Имена преподавателей, зав. кафедрами и деканов (full_name, head_full_name, dean_full_name) разрешены к прямому выводу.

ФОРМАТ ОТВЕТА:
Возвращай ответ СТРОГО в формате JSON без markdown-разметки:
{
  "sql": "SELECT ...",
  "explanation": {
    "tables": ["список таблиц"],
    "joins": ["описание связей JOIN"],
    "filters": ["примененные условия WHERE"],
    "aggregations": ["примененные агрегаты COUNT/AVG/SUM"],
    "limit": "значение лимита"
  },
  "summary_ru": "Краткое описание на русском языке того, что делает этот запрос."
}
"""

async def generate_sql_and_explanation(user_question: str) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.0,
            "maxTokens": "2000"
        },
        "messages": [
            {"role": "system", "text": SYSTEM_PROMPT},
            {"role": "user", "text": user_question}
        ]
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(YANDEX_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        raw_text = response.json()["result"]["alternatives"][0]["message"]["text"]

    cleaned_text = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE)
    
    json_match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0))
    
    return json.loads(cleaned_text)