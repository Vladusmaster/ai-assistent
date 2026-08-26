import json
import os
import re
import html
import httpx
from typing import Any, Dict
from dotenv import load_dotenv

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "").strip()
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "").strip()
YANDEX_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

SYSTEM_PROMPT = """
Ты — AI-ассистент базы данных PostgreSQL РЭУ им. Г. В. Плеханова.
Генерируй точный SQL-запрос (PostgreSQL dialect) и формируй структурированный блок Explainable AI.

АКТУАЛЬНАЯ СХЕМА БАЗЫ ДАННЫХ:
1. faculties (id, name, short_name, dean_full_name, building, email)
2. departments (id, faculty_id, name, head_full_name)
3. teachers (id, department_id, full_name, academic_degree, academic_title, position, email)
4. programs (id, faculty_id, program_code, name, education_level, budget_places, commercial_places, special_quota, target_quota, separate_quota, annual_tuition_fee)
5. applicants (id, snils, full_name, birth_date, passport_number, education_doc_type, doc_issue_year, school_name)
6. applications (id, application_number, applicant_id, program_id, campaign_year, priority, study_form, admission_basis, quota_type, score_russian, score_math, elective_subject, score_elective, score_dvi, score_achievements, achievement_type, total_score, is_original_submitted, is_consent_submitted, status, enrollment_order_number, enrollment_order_date, submission_date)
7. students (id, program_id, student_card_number, study_group, study_year, admission_year, education_basis, student_status)
8. classrooms (id, building, room_number, capacity, room_type)
9. disciplines (id, department_id, teacher_id, name, semester, academic_hours, control_form)
10. grades (id, student_id, discipline_id, semester, points, grade, has_academic_debt, exam_date)
11. schedules (id, classroom_id, discipline_id, day_of_week, time_slot, study_group, attendees_count)

ПРАВИЛА БЕЗОПАСНОСТИ И ПЕРСОНАЛЬНЫХ ДАННЫХ:
1. РАЗРЕШЕНО выводить ФИО преподавателей (teachers.full_name), заведующих кафедрами (departments.head_full_name), деканов (faculties.dean_full_name).
2. СТРОГО ЗАПРЕЩЕНО извлекать поля passport_number, snils, birth_date, applicants.full_name.
3. По студентам и абитуриентам выводятся только агрегированные показатели (COUNT, AVG, MAX, MIN) или обезличенные данные (application_number, student_card_number, study_group, баллы).
4. Используй правильные JOIN-связи через первичные и внешние ключи.

ФОРМАТ ОТВЕТА (СТРОГО JSON):
{
  "sql": "SELECT ...",
  "explanation": {
    "tables": ["список задействованных таблиц"],
    "joins": ["описание связей между таблицами"],
    "filters": ["условия фильтрации WHERE"],
    "aggregations": ["примененные функции агрегации"],
    "limit": "значение ограничения строк"
  },
  "summary_ru": "Понятное объяснение на русском языке, что возвращает этот запрос."
}
"""

def sanitize_user_input(text: str) -> str:
    cleaned = text.strip()
    cleaned = html.escape(cleaned)
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)
    return cleaned[:400]

async def generate_sql_and_explanation(user_question: str) -> Dict[str, Any]:
    safe_question = sanitize_user_input(user_question)
    
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
            {"role": "user", "text": safe_question}
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

async def ask_yandex_gpt_analytics(logs_context: str) -> str:
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Проанализируй список последних пользовательских запросов к базе данных университета:
    {logs_context}
    
    Сформируй краткую аналитическую сводку (3-4 предложения):
    1. Какие темы больше всего интересуют пользователей (абитуриенты, оценки, кафедры, преподаватели).
    2. Были ли зафиксированы попытки вредоносных запросов.
    3. Рекомендация руководству по оптимизации данных.
    """
    
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {"stream": False, "temperature": 0.2, "maxTokens": "1000"},
        "messages": [{"role": "user", "text": prompt}]
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(YANDEX_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["result"]["alternatives"][0]["message"]["text"]
    except Exception as e:
        return "Аналитика временно недоступна."