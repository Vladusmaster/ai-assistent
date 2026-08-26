# ==============================================================================
# ФАЙЛ: backend/llm.py (ЗАМЕНИТЬ ПОЛНОСТЬЮ)
# ==============================================================================

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

ТОЧНАЯ СХЕМА БАЗЫ ДАННЫХ И СВЯЗИ (FOREIGN KEYS):
1. faculties (id, name, short_name, dean_full_name, building, email)
2. departments (id, faculty_id, name, head_full_name)
   -> departments.faculty_id = faculties.id
3. teachers (id, department_id, full_name, academic_degree, academic_title, position, email)
   -> teachers.department_id = departments.id
4. programs (id, faculty_id, program_code, name, education_level, budget_places, commercial_places, special_quota, target_quota, separate_quota, annual_tuition_fee)
   -> programs.faculty_id = faculties.id
5. applicants (id, snils, full_name, birth_date, passport_number, education_doc_type, doc_issue_year, school_name)
6. applications (id, application_number, applicant_id, program_id, campaign_year, priority, study_form, admission_basis, quota_type, score_russian, score_math, elective_subject, score_elective, score_dvi, score_achievements, achievement_type, total_score, is_original_submitted, is_consent_submitted, status, enrollment_order_number, enrollment_order_date, submission_date)
   -> applications.applicant_id = applicants.id
   -> applications.program_id = programs.id
7. students (id, program_id, student_card_number, study_group, study_year, admission_year, education_basis, student_status)
   -> students.program_id = programs.id
8. classrooms (id, building, room_number, capacity, room_type)
9. disciplines (id, department_id, teacher_id, name, semester, academic_hours, control_form)
   -> disciplines.department_id = departments.id
   -> disciplines.teacher_id = teachers.id
10. grades (id, student_id, discipline_id, semester, points, grade, has_academic_debt, exam_date)
   -> grades.student_id = students.id
   -> grades.discipline_id = disciplines.id
11. schedules (id, classroom_id, discipline_id, day_of_week, time_slot, study_group, attendees_count)
   -> schedules.classroom_id = classrooms.id
   -> schedules.discipline_id = disciplines.id

ОБРАБОТКА НЕКОРРЕКТНОГО / СЛУЧАЙНОГО ВВОДА:
Если запрос пользователя:
- представляет собой случайный набор букв/символов (например: "jstr", "фывфыв", "asdf"),
- является общим приветствием ("привет", "здравствуйте") без вопроса к БД,
- не имеет отношения к университету и его данным,
ТОГДА:
- Установи "sql": ""
- Оставь "explanation": {}
- В поле "summary_ru" вежливо напиши: "Не удалось распознать вопрос. Пожалуйста, уточните запрос (например: направления подготовки, список кафедр, преподаватели или статистика заявлений РЭУ)."

ПРАВИЛА БЕЗОПАСНОСТИ:
1. Выводи только существующие столбцы.
2. Строго запрещен вывод passport_number, snils, birth_date, applicants.full_name.
3. По студентам и абитуриентам выводи агрегаты (COUNT, AVG) или обезличенные номера (application_number, student_card_number).

ФОРМАТ ОТВЕТА (СТРОГО JSON):
{
  "sql": "SELECT ...",
  "explanation": {
    "tables": ["таблицы"],
    "joins": ["связи JOIN"],
    "filters": ["условия WHERE"],
    "aggregations": ["агрегатные функции"],
    "limit": "лимит"
  },
  "summary_ru": "Понятное объяснение на русском языке."
}
"""

def sanitize_user_input(text: str) -> str:
    cleaned = text.strip()
    cleaned = html.escape(cleaned)
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)
    return cleaned[:400]

def parse_llm_json(raw_text: str) -> Dict[str, Any]:
    default_fallback = {
        "sql": "",
        "explanation": {},
        "summary_ru": "Не удалось распознать вопрос. Пожалуйста, сформулируйте запрос о данных университета (например: кафедры, преподаватели, программы подготовки)."
    }
    
    if not raw_text or not raw_text.strip():
        return default_fallback

    cleaned_text = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE)
    
    # 1. Поиск JSON внутри фигурных скобок
    json_match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except Exception:
            pass

    # 2. Попытка прямого парсинга
    try:
        return json.loads(cleaned_text)
    except Exception:
        # Если модель вернула plain-text отказ или цензурный ответ
        return default_fallback

async def generate_sql_and_explanation(user_question: str) -> Dict[str, Any]:
    safe_question = sanitize_user_input(user_question)
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {"stream": False, "temperature": 0.0, "maxTokens": "2000"},
        "messages": [
            {"role": "system", "text": SYSTEM_PROMPT},
            {"role": "user", "text": safe_question}
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(YANDEX_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            result_json = response.json()
            
            alternatives = result_json.get("result", {}).get("alternatives", [])
            if not alternatives:
                return parse_llm_json("")
                
            raw_text = alternatives[0].get("message", {}).get("text", "")
            return parse_llm_json(raw_text)
            
    except Exception as e:
        return {
            "sql": "",
            "explanation": {},
            "summary_ru": "Не удалось обработать запрос. Пожалуйста, уточните ваш вопрос."
        }

async def fix_sql_with_error(user_question: str, faulty_sql: str, error_msg: str) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    correction_prompt = f"""
    Вопрос пользователя: "{user_question}"
    Твой предыдущий SQL-запрос:
    {faulty_sql}
    
    СУБД PostgreSQL вернула ошибку:
    {error_msg}
    
    Исправь SQL-запрос строго в соответствии со схемой таблиц и верни корректный JSON. Если запрос невозможно составить, верни "sql": "".
    """
    
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {"stream": False, "temperature": 0.0, "maxTokens": "2000"},
        "messages": [
            {"role": "system", "text": SYSTEM_PROMPT},
            {"role": "user", "text": correction_prompt}
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(YANDEX_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            result_json = response.json()
            
            alternatives = result_json.get("result", {}).get("alternatives", [])
            if not alternatives:
                return parse_llm_json("")
                
            raw_text = alternatives[0].get("message", {}).get("text", "")
            return parse_llm_json(raw_text)
    except Exception:
        return parse_llm_json("")

async def ask_yandex_gpt_analytics(logs_context: str) -> str:
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Проанализируй список последних пользовательских запросов к базе данных университета:
    {logs_context}
    
    Сформируй краткую аналитическую сводку (3-4 предложения):
    1. Какие темы больше всего интересуют пользователей.
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
    except Exception:
        return "Аналитика временно недоступна."