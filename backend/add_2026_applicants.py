# ==============================================================================
# ФАЙЛ: backend/add_2026_applicants.py (НОВЫЙ ФАЙЛ)
# ==============================================================================

import asyncio
import os
import random
from datetime import date
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "185.241.193.203").strip()
DB_PORT = int(os.getenv("DB_PORT", "5432").strip())
DB_NAME = os.getenv("DB_NAME", "vesna-db5").strip()
DB_USER = os.getenv("DB_USER", "vdb5_user").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "X59b39C9-5D4X4NHn").strip()

FIRST_NAMES_M = ["Александр", "Михаил", "Дмитрий", "Сергей", "Андрей", "Алексей", "Артем", "Илья", "Владислав", "Иван", "Кирилл", "Максим"]
FIRST_NAMES_F = ["Анна", "Мария", "Елена", "Ольга", "Екатерина", "Татьяна", "Наталья", "Ирина", "Светлана", "Юлия", "Полина", "Алиса"]
LAST_NAMES_M = ["Иванов", "Смирнов", "Кузнецов", "Попов", "Васильев", "Петров", "Соколов", "Михайлов", "Новиков", "Федоров", "Морозов", "Волков"]
LAST_NAMES_F = ["Иванова", "Смирнова", "Кузнецова", "Попова", "Васильева", "Петрова", "Соколова", "Михайлова", "Новикова", "Федорова", "Морозова", "Волкова"]
PATRONYMICS_M = ["Александрович", "Сергеевич", "Дмитриевич", "Андреевич", "Владимирович", "Игоревич", "Михайлович", "Артемович"]
PATRONYMICS_F = ["Александровна", "Сергеевна", "Дмитриевна", "Андреевна", "Владимировна", "Игоревна", "Михайловна", "Артемовна"]

CHOICE_SUBJECTS = ["Информатика и ИКТ", "Обществознание", "Физика", "Иностранный язык (Английский)", "История", "География", "Химия", "Биология"]
ACHIEVEMENTS = [
    ("Нет", 0),
    ("Аттестат с отличием (Золотая медаль)", 5),
    ("Диплом победителя Всероссийской олимпиады школьников", 10),
    ("Призер олимпиады школьников РЭУ", 7),
    ("Золотой значок ГТО", 2),
    ("Волонтерская деятельность (книжка волонтера)", 2),
    ("Аттестат с отличием и значок ГТО", 7),
    ("Победитель чемпионата высоких технологий", 10)
]
QUOTAS = ["Без квот", "Особая квота (инвалидность/сироты)", "Целевая квота (договор с организацией)", "Отдельная квота (участники СВО и их дети)"]
DOC_TYPES = ["Аттестат о среднем общем образовании", "Аттестат с отличием", "Диплом СПО с отличием"]
SCHOOLS = ["Экономический лицей РЭУ", "МАОУ Лицей №1580", "ГБОУ Школа №1535", "ГБОУ Лицей «Вторая школа»", "ГБОУ Школа №57", "ГБПОУ Колледж связи №54"]

def generate_full_name():
    if random.random() > 0.5:
        return f"{random.choice(LAST_NAMES_M)} {random.choice(FIRST_NAMES_M)} {random.choice(PATRONYMICS_M)}"
    return f"{random.choice(LAST_NAMES_F)} {random.choice(FIRST_NAMES_F)} {random.choice(PATRONYMICS_F)}"

def generate_snils(idx: int) -> str:
    p1 = random.randint(100, 999)
    p2 = random.randint(100, 999)
    p3 = (idx % 900) + 100
    chk = random.randint(10, 99)
    return f"{p1:03d}-{p2:03d}-{p3:03d} {chk:02d}"

async def add_2026_applicants():
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    programs = await conn.fetch("SELECT id FROM programs")
    program_ids = [r["id"] for r in programs]

    max_app_id = await conn.fetchval("SELECT COALESCE(MAX(id), 0) FROM applicants")
    max_application_id = await conn.fetchval("SELECT COALESCE(MAX(id), 0) FROM applications")

    print(f"Добавление 400 новых абитуриентов 2026 года...")
    applicant_ids = []
    for i in range(1, 401):
        fio = generate_full_name()
        b_year = random.randint(2007, 2009)
        b_date = date(b_year, random.randint(1, 12), random.randint(1, 28))
        snils = generate_snils(max_app_id + i)
        passport = f"{random.randint(4500, 4620)} {random.randint(100000, 999999)}"
        doc_type = random.choice(DOC_TYPES)
        school = random.choice(SCHOOLS)

        aid = await conn.fetchval(
            """INSERT INTO applicants (snils, full_name, birth_date, passport_number, education_doc_type, doc_issue_year, school_name)
               VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id""",
            snils, fio, b_date, passport, doc_type, 2026, school
        )
        applicant_ids.append(aid)

    print(f"Формирование 1000 заявлений приемной кампании 2026 года...")
    app_records = []
    app_counter = max_application_id + 1

    for aid in applicant_ids:
        chosen_programs = random.sample(program_ids, k=random.randint(2, 4))
        for priority, prog_id in enumerate(chosen_programs, start=1):
            if len(app_records) >= 1000:
                break

            app_num = f"РЭУ-2026-{app_counter:05d}"
            app_counter += 1

            form = random.choice(["Очная", "Очно-заочная"])
            basis = random.choice(["Бюджетные места", "Платная основа", "Особая квота", "Целевая квота", "Отдельная квота"])
            quota_type = random.choice(QUOTAS) if basis != "Платная основа" else "Без квот"

            math_s = random.randint(60, 100)
            rus_s = random.randint(65, 100)
            choice_sub = random.choice(CHOICE_SUBJECTS)
            choice_s = random.randint(55, 100)
            dvi_s = random.choice([0, 0, random.randint(65, 98)])

            ach_title, ach_score = random.choice(ACHIEVEMENTS)
            total_s = math_s + rus_s + choice_s + dvi_s + ach_score

            original = (priority == 1 and random.random() > 0.35)
            consent = original and (random.random() > 0.3)

            # Статусы актуальной кампании 2026 года
            if total_s >= 270 and original and consent:
                status = "Зачислен"
                order_num = f"ПР-З/2026-{random.randint(100, 450)}"
                order_date = date(2026, 8, random.randint(3, 10))
            elif consent:
                status = "Ожидает согласия на зачисление"
                order_num, order_date = None, None
            else:
                status = random.choice(["Принято", "Участвует в конкурсе"])
                order_num, order_date = None, None

            sub_date = date(2026, random.randint(6, 7), random.randint(1, 25))

            app_records.append((
                app_num, aid, prog_id, 2026, priority, form, basis, quota_type,
                rus_s, math_s, choice_sub, choice_s, dvi_s,
                ach_score, ach_title, total_s, original, consent, status,
                order_num, order_date, sub_date
            ))

    await conn.executemany(
        """INSERT INTO applications (
            application_number, applicant_id, program_id, campaign_year, priority,
            study_form, admission_basis, quota_type, score_russian,
            score_math, elective_subject, score_elective, score_dvi,
            score_achievements, achievement_type, total_score,
            is_original_submitted, is_consent_submitted, status, enrollment_order_number,
            enrollment_order_date, submission_date
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)""",
        app_records
    )

    total_2026 = await conn.fetchval("SELECT count(*) FROM applications WHERE campaign_year = 2026")
    enrolled_2026 = await conn.fetchval("SELECT count(*) FROM applications WHERE campaign_year = 2026 AND status = 'Зачислен'")

    await conn.close()
    print(f"\nДанные за 2026 год успешно записаны:")
    print(f"- Всего заявлений за 2026 год: {total_2026}")
    print(f"- Зачислено абитуриентов в 2026 году: {enrolled_2026}")

if __name__ == "__main__":
    asyncio.run(add_2026_applicants())