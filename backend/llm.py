import json
import os
import re
import html
import httpx
from datetime import date
from typing import Any, Dict
from dotenv import load_dotenv

load_dotenv()

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "").strip()
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "").strip()
YANDEX_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

def get_system_prompt(role: str = "applicant") -> str:
    today = date.today()
    current_year = today.year

    role_rules = {
        "applicant": """
РОЛЬ ПОЛЬЗОВАТЕЛЯ: АБИТУРИЕНТ
- Разрешено: программы, проходные баллы, кафедры, деканы, преподаватели, аудитории, АГРЕГИРОВАННАЯ статистика успеваемости.
- СТРОГО ЗАПРЕЩЕНО выводить индивидуальные записи оценок из grades (SELECT * FROM grades, student_id, points построчно) и ФИО студентов.
- По успеваемости разрешены ТОЛЬКО агрегаты (AVG(points), COUNT(*)).
        """,
        "student": """
РОЛЬ ПОЛЬЗОВАТЕЛЯ: СТУДЕНТ
- Разрешено: расписание, предметы, успеваемость (grades), кафедры, преподаватели.
- Чужие данные других студентов выводятся исключительно в обезличенном или агрегированном виде.
        """,
        "teacher": """
РОЛЬ ПОЛЬЗОВАТЕЛЯ: ПРЕПОДАВАТЕЛЬ
- Разрешено: ведомости, оценки (grades), расписание (schedules), списки студентов с ФИО (students.full_name) для проведения занятий.
- Запрещено: персональные данные абитуриентов (applicants).
        """,
        "admin": """
РОЛЬ ПОЛЬЗОВАТЕЛЯ: АДМИНИСТРАЦИЯ / ДЕКАНАТ
- Полный доступ ко всей аналитике, успеваемости, ФИО студентов и преподавателей.
        """
    }

    selected_role_rule = role_rules.get(role, role_rules["applicant"])

    return f"""
Ты — AI-ассистент базы данных PostgreSQL РЭУ им. Г. В. Плеханова.
Генерируй точный SQL-запрос (PostgreSQL dialect) и формируй структурированный блок Explainable AI.

ВРЕМЕННОЙ КОНТЕКСТ:
- Текущий год: {current_year}.
- Если указаны «последние N дней кампании X года», вычисляй интервал от максимальной даты подачи документов за этот год:
  submission_date >= (SELECT MAX(submission_date) - INTERVAL '7 days' FROM applications WHERE campaign_year = 2025) AND campaign_year = 2025

ПРАВИЛА ТИПИЗАЦИИ И СТОЛБЦОВ (КРИТИЧЕСКИ ВАЖНО):
1. disciplines.semester — это INTEGER (число от 1 до 8).
   - «Весенний семестр» -> semester IN (2, 4, 6, 8) или (semester % 2 = 0).
   - «Осенний семестр» -> semester IN (1, 3, 5, 7) или (semester % 2 = 1).
   - ЗАПРЕЩЕНО писать `semester ILIKE ...`!
2. grades.points — это INTEGER (баллы от 0 до 100). Для среднего балла ВСЕГДА используй `AVG(grades.points)`.
3. grades.grade — это VARCHAR ('5 (Отл)', '4 (Хор)', '3 (Удовл)', '2 (Неуд)'). ЗАПРЕЩЕНО делать `AVG(grade)`!
4. «Успешно сдал экзамен» -> (grades.has_academic_debt = false) или (grades.points >= 50).
5. «Не сдал ни одного экзамена / только задолженности» ->
   SELECT students.id, students.full_name, students.study_group
   FROM students
   JOIN grades ON students.id = grades.student_id
   GROUP BY students.id, students.full_name, students.study_group
   HAVING bool_and(grades.has_academic_debt = true);
6. «Средняя учебная нагрузка на преподавателя по кафедре» ->
   SELECT departments.name, SUM(disciplines.academic_hours)::float / NULLIF(COUNT(DISTINCT teachers.id), 0) AS avg_hours
   FROM departments
   JOIN teachers ON departments.id = teachers.department_id
   JOIN disciplines ON teachers.id = disciplines.teacher_id
   GROUP BY departments.name
   HAVING (SUM(disciplines.academic_hours)::float / NULLIF(COUNT(DISTINCT teachers.id), 0)) > 250;
7. Сравнение «средний балл кафедры ниже среднего по университету»:
   WITH uni_avg AS (SELECT AVG(points) AS val FROM grades)
   SELECT departments.name, AVG(grades.points) AS dept_avg
   FROM departments
   JOIN teachers ON departments.id = teachers.department_id
   JOIN disciplines ON teachers.id = disciplines.teacher_id
   JOIN grades ON disciplines.id = grades.discipline_id
   CROSS JOIN uni_avg
   GROUP BY departments.name, uni_avg.val
   HAVING AVG(grades.points) < uni_avg.val;

СВЯЗИ СУЩНОСТЕЙ:
- Факультеты и институты (ВШКМиС, ВШЭиБ, ВШФ, IT) -> faculties (name, short_name).
- Поиск по тексту ВСЕГДА через `ILIKE '%...%'`.

{selected_role_rule}

АКТУАЛЬНАЯ СХЕМА БАЗЫ ДАННЫХ:
1. faculties (id, name, short_name, dean_full_name, building, email)
2. departments (id, faculty_id, name, head_full_name)
3. teachers (id, department_id, full_name, academic_degree, academic_title, position, email)
4. programs (id, faculty_id, program_code, name, education_level, budget_places, commercial_places, special_quota, target_quota, separate_quota, annual_tuition_fee)
5. applicants (id, snils, full_name, birth_date, passport_number, education_doc_type, doc_issue_year, school_name)
6. applications (id, application_number, applicant_id, program_id, campaign_year, priority, study_form, admission_basis, quota_type, score_russian, score_math, elective_subject, score_elective, score_dvi, score_achievements, achievement_type, total_score, is_original_submitted, is_consent_submitted, status, enrollment_order_number, enrollment_order_date, submission_date)
7. students (id, program_id, full_name, student_card_number, study_group, study_year, admission_year, education_basis, student_status)
8. classrooms (id, building, room_number, capacity, room_type)
9. disciplines (id, department_id, teacher_id, name, semester, academic_hours, control_form)
10. grades (id, student_id, discipline_id, semester, points, grade, has_academic_debt, exam_date)
11. schedules (id, classroom_id, discipline_id, day_of_week, time_slot, study_group, attendees_count)

ФОРМАТ ОТВЕТА (СТРОГО JSON):
{{
  "sql": "SELECT ...",
  "explanation": {{
    "tables": ["таблицы"],
    "joins": ["связи JOIN"],
    "filters": ["условия WHERE"],
    "aggregations": ["агрегатные функции"],
    "limit": "лимит"
  }},
  "summary_ru": "Понятное объяснение на русском языке."
}}
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
        "summary_ru": "Не удалось распознать вопрос. Пожалуйста, сформулируйте запрос о структуре или аналитике университета."
    }
    
    if not raw_text or not raw_text.strip():
        return default_fallback

    cleaned_text = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE)
    
    json_match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except Exception:
            pass

    try:
        return json.loads(cleaned_text)
    except Exception:
        return default_fallback

async def generate_sql_and_explanation(user_question: str, role: str = "applicant") -> Dict[str, Any]:
    safe_question = sanitize_user_input(user_question)
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {"stream": False, "temperature": 0.0, "maxTokens": "2000"},
        "messages": [
            {"role": "system", "text": get_system_prompt(role)},
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
            
    except Exception:
        return {
            "sql": "",
            "explanation": {},
            "summary_ru": "Не удалось обработать запрос. Пожалуйста, уточните ваш вопрос."
        }

async def fix_sql_with_error(user_question: str, faulty_sql: str, error_msg: str, role: str = "applicant") -> Dict[str, Any]:
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
    
    Исправь SQL-запрос строго в соответствии со схемой таблиц, правильными типами данных (semester - число, points - число) и связями. Верни корректный JSON.
    """
    
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {"stream": False, "temperature": 0.0, "maxTokens": "2000"},
        "messages": [
            {"role": "system", "text": get_system_prompt(role)},
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