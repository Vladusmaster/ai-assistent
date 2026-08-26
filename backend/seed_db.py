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

DDL_SCHEMA = """
DROP TABLE IF EXISTS query_logs CASCADE;
DROP TABLE IF EXISTS schedules CASCADE;
DROP TABLE IF EXISTS grades CASCADE;
DROP TABLE IF EXISTS disciplines CASCADE;
DROP TABLE IF EXISTS classrooms CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS applicants CASCADE;
DROP TABLE IF EXISTS programs CASCADE;
DROP TABLE IF EXISTS teachers CASCADE;
DROP TABLE IF EXISTS departments CASCADE;
DROP TABLE IF EXISTS faculties CASCADE;

CREATE TABLE faculties (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    short_name VARCHAR(50) NOT NULL,
    dean_full_name VARCHAR(255) NOT NULL,
    building VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL
);

CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    faculty_id INT NOT NULL REFERENCES faculties(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    head_full_name VARCHAR(255) NOT NULL
);

CREATE TABLE teachers (
    id SERIAL PRIMARY KEY,
    department_id INT NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    academic_degree VARCHAR(100) NOT NULL,
    academic_title VARCHAR(100) NOT NULL,
    position VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL
);

CREATE TABLE programs (
    id SERIAL PRIMARY KEY,
    faculty_id INT NOT NULL REFERENCES faculties(id) ON DELETE CASCADE,
    program_code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    education_level VARCHAR(50) NOT NULL,
    budget_places INT NOT NULL DEFAULT 0,
    commercial_places INT NOT NULL DEFAULT 0,
    special_quota INT NOT NULL DEFAULT 0,
    target_quota INT NOT NULL DEFAULT 0,
    separate_quota INT NOT NULL DEFAULT 0,
    annual_tuition_fee INT NOT NULL DEFAULT 0
);

CREATE TABLE applicants (
    id SERIAL PRIMARY KEY,
    snils VARCHAR(14) NOT NULL UNIQUE,
    full_name VARCHAR(255) NOT NULL,
    birth_date DATE NOT NULL,
    passport_number VARCHAR(20) NOT NULL,
    education_doc_type VARCHAR(100) NOT NULL,
    doc_issue_year INT NOT NULL,
    school_name VARCHAR(255) NOT NULL
);

CREATE TABLE applications (
    id SERIAL PRIMARY KEY,
    application_number VARCHAR(64) NOT NULL UNIQUE,
    applicant_id INT NOT NULL REFERENCES applicants(id) ON DELETE CASCADE,
    program_id INT NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    campaign_year INT NOT NULL,
    priority INT NOT NULL,
    study_form VARCHAR(50) NOT NULL,
    admission_basis VARCHAR(100) NOT NULL,
    quota_type VARCHAR(100) NOT NULL DEFAULT 'Без квот',
    score_russian INT NOT NULL,
    score_math INT NOT NULL,
    elective_subject VARCHAR(100) NOT NULL,
    score_elective INT NOT NULL,
    score_dvi INT NOT NULL DEFAULT 0,
    score_achievements INT NOT NULL DEFAULT 0,
    achievement_type VARCHAR(200) NOT NULL DEFAULT 'Нет',
    total_score INT NOT NULL,
    is_original_submitted BOOLEAN NOT NULL DEFAULT FALSE,
    is_consent_submitted BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(100) NOT NULL,
    enrollment_order_number VARCHAR(100),
    enrollment_order_date DATE,
    submission_date DATE NOT NULL
);

CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    program_id INT NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    student_card_number VARCHAR(64) NOT NULL UNIQUE,
    study_group VARCHAR(50) NOT NULL,
    study_year INT NOT NULL,
    admission_year INT NOT NULL,
    education_basis VARCHAR(50) NOT NULL,
    student_status VARCHAR(50) NOT NULL
);

CREATE TABLE classrooms (
    id SERIAL PRIMARY KEY,
    building VARCHAR(50) NOT NULL,
    room_number VARCHAR(20) NOT NULL,
    capacity INT NOT NULL,
    room_type VARCHAR(50) NOT NULL
);

CREATE TABLE disciplines (
    id SERIAL PRIMARY KEY,
    department_id INT NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    teacher_id INT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    semester INT NOT NULL,
    academic_hours INT NOT NULL,
    control_form VARCHAR(50) NOT NULL
);

CREATE TABLE grades (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    discipline_id INT NOT NULL REFERENCES disciplines(id) ON DELETE CASCADE,
    semester INT NOT NULL,
    points INT NOT NULL,
    grade VARCHAR(20) NOT NULL,
    has_academic_debt BOOLEAN NOT NULL DEFAULT FALSE,
    exam_date DATE NOT NULL
);

CREATE TABLE schedules (
    id SERIAL PRIMARY KEY,
    classroom_id INT NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    discipline_id INT NOT NULL REFERENCES disciplines(id) ON DELETE CASCADE,
    day_of_week INT NOT NULL,
    time_slot VARCHAR(50) NOT NULL,
    study_group VARCHAR(50) NOT NULL,
    attendees_count INT NOT NULL
);
"""

FIRST_NAMES_M = ["Александр", "Михаил", "Дмитрий", "Сергей", "Андрей", "Алексей", "Артем", "Илья", "Владислав", "Иван"]
FIRST_NAMES_F = ["Анна", "Мария", "Елена", "Ольга", "Екатерина", "Татьяна", "Наталья", "Ирина", "Светлана", "Юлия"]
LAST_NAMES_M = ["Иванов", "Смирнов", "Кузнецов", "Попов", "Васильев", "Петров", "Соколов", "Михайлов", "Новиков", "Федоров"]
LAST_NAMES_F = ["Иванова", "Смирнова", "Кузнецова", "Попова", "Васильева", "Петрова", "Соколова", "Михайлова", "Новикова", "Федорова"]
PATRONYMICS_M = ["Александрович", "Сергеевич", "Дмитриевич", "Андреевич", "Владимирович", "Игоревич", "Михайлович"]
PATRONYMICS_F = ["Александровна", "Сергеевна", "Дмитриевна", "Андреевна", "Владимировна", "Игоревна", "Михайловна"]

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
DOC_TYPES = ["Аттестат о среднем общем образовании", "Аттестат с отличием", "Диплом СПО с отличием", "Диплом СПО"]
SCHOOLS = ["МАОУ Лицей №1580", "ГБОУ Школа №1535", "ГБОУ Лицей «Вторая школа»", "ГБПОУ Колледж связи №54", "ГБОУ Школа №57", "Экономический лицей РЭУ", "МАОУ Гимназия №9 г. Екатеринбург", "МАОУ Лицей №130 г. Новосибирск"]

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

async def seed():
    print(f"Подключение к базе данных {DB_NAME}...")
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    
    print("Создание схемы таблиц...")
    await conn.execute(DDL_SCHEMA)

    faculties_data = [
        ("Высшая школа кибертехнологий, математики и статистики", "ВШ КМиС", "Титов Валерий Александрович", "Корпус 9 (Зацепа, 41с4)", "cyber@rea.ru"),
        ("Высшая школа экономики и бизнеса", "ВШЭиБ", "Забелина Ольга Викторовна", "Корпус 1 (Стремянный пер., 28)", "vsheb@rea.ru"),
        ("Высшая школа финансов", "ВШФ", "Школик Олег Александрович", "Корпус 2 (Стремянный пер., 28с1)", "vshf@rea.ru"),
        ("Высшая школа менеджмента", "ВШМ", "Пономарев Максим Александрович", "Корпус 6 (Зацепа, 41)", "vshm@rea.ru"),
        ("Высшая школа права", "ВШП", "Экимов Алик Исмаилович", "Корпус 8 (Зацепа, 43)", "law@rea.ru"),
        ("Высшая школа социально-гуманитарных наук", "ВШСГН", "Кошкин Андрей Петрович", "Корпус 3 (Стремянный пер., 36)", "vshsgn@rea.ru"),
        ("Высшая школа креативных индустрий", "ВШКИ", "Архипова Марина Борисовна", "Корпус 3 (Стремянный пер., 36)", "vshki@rea.ru"),
        ("Высшая инженерная школа «Новые материалы и технологии»", "ВИШ НМиТ", "Квитко Владимир Анатольевич", "Корпус 2 (Стремянный пер., 28с1)", "vish@rea.ru"),
        ("Специальный факультет талантливой молодёжи «Форсайт»", "СФТМ Форсайт", "Зулькарнай Рустем Анварович", "Корпус 1 (Стремянный пер., 28)", "foresight@rea.ru"),
        ("Институт «Первая Академия медиа»", "ПАМ", "Богданов Вадим Евгеньевич", "Корпус 6 (Зацепа, 41)", "media@rea.ru"),
        ("Плехановская школа бизнеса «Интеграл»", "ПШБ Интеграл", "Лаптева Анна Евгеньевна", "Корпус 1 (Стремянный пер., 28)", "integral@rea.ru")
    ]
    faculty_ids = []
    for f in faculties_data:
        fid = await conn.fetchval(
            'INSERT INTO faculties (name, short_name, dean_full_name, building, email) VALUES ($1, $2, $3, $4, $5) RETURNING id',
            *f
        )
        faculty_ids.append(fid)

    departments_data = [
        (faculty_ids[0], "Кафедра прикладной информатики и информационной безопасности", "Сухоруков Андрей Сергеевич"),
        (faculty_ids[0], "Кафедра статистики и анализа данных", "Карманов Михаил Владимирович"),
        (faculty_ids[1], "Кафедра экономической теории", "Устюжанина Елена Владимировна"),
        (faculty_ids[1], "Кафедра мировой экономики", "Хасбулатов Руслан Имранович"),
        (faculty_ids[2], "Кафедра банковского дела и монетарного регулирования", "Горохова Диана Викторовна"),
        (faculty_ids[2], "Кафедра финансового контроля и аудита", "Прокофьев Станислав Евгеньевич"),
        (faculty_ids[3], "Кафедра общего и стратегического менеджмента", "Сидоров Олег Николаевич"),
        (faculty_ids[3], "Кафедра индустрии гостеприимства и туризма", "Печенина Ольга Владимировна"),
        (faculty_ids[4], "Кафедра гражданско-правовых дисциплин", "Курбанов Рашад Афатович"),
        (faculty_ids[4], "Кафедра государственного и муниципального управления", "Гришин Константин Евгеньевич"),
        (faculty_ids[5], "Кафедра социологии и политологии", "Буланов Владимир Викторович"),
        (faculty_ids[5], "Кафедра общей и прикладной психологии", "Васильева Инна Викторовна"),
        (faculty_ids[6], "Кафедра рекламы, связей с общественностью и дизайна", "Скоробогатых Ирина Ивановна"),
        (faculty_ids[6], "Кафедра цифровых медиакоммуникаций", "Алексеев Андрей Юрьевич"),
        (faculty_ids[7], "Кафедра товароведения и таможенной экспертизы", "Карасев Михаил Александрович"),
        (faculty_ids[7], "Кафедра полимерных материалов и технологий", "Попов Анатолий Анатольевич"),
        (faculty_ids[8], "Кафедра высших междисциплинарных исследований Data Science", "Зайцев Владимир Кириллович"),
        (faculty_ids[8], "Кафедра математического моделирования бизнес-систем", "Романова Светлана Юрьевна"),
        (faculty_ids[9], "Кафедра телевидения и медиапроизводства", "Селезнев Артем Владимирович"),
        (faculty_ids[9], "Кафедра периодической печати и сетевых изданий", "Кузнецова Галина Николаевна"),
        (faculty_ids[10], "Кафедра бизнес-администрирования и стартапов", "Мельников Анатолий Борисович"),
        (faculty_ids[10], "Кафедра корпоративного управления MBA", "Лебедев Виктор Михайлович")
    ]
    department_ids = []
    for d in departments_data:
        did = await conn.fetchval(
            'INSERT INTO departments (faculty_id, name, head_full_name) VALUES ($1, $2, $3) RETURNING id',
            *d
        )
        department_ids.append(did)

    degrees = ["д.э.н.", "д.т.н.", "к.э.н.", "к.т.н.", "к.ф.-м.н.", "к.ю.н.", "д.социол.н."]
    titles = ["Профессор", "Доцент", "Старший преподаватель", "Ассистент"]
    positions = ["Профессор кафедры", "Доцент кафедры", "Старший преподаватель", "Преподаватель"]

    teacher_ids = []
    for dept_id in department_ids:
        for _ in range(3):
            t_name = generate_full_name()
            email = f"t.{random.randint(1000, 9999)}@rea.ru"
            tid = await conn.fetchval(
                """INSERT INTO teachers (department_id, full_name, academic_degree, academic_title, position, email)
                   VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
                dept_id, t_name, random.choice(degrees), random.choice(titles), random.choice(positions), email
            )
            teacher_ids.append((tid, dept_id))

    programs_data = [
        (faculty_ids[0], "09.03.03", "Прикладная информатика в экономике", "Бакалавриат", 50, 70, 5, 5, 5, 360000),
        (faculty_ids[0], "09.03.01", "Информатика и вычислительная техника", "Бакалавриат", 45, 55, 5, 4, 4, 370000),
        (faculty_ids[0], "01.03.02", "Прикладная математика и информатика", "Бакалавриат", 35, 40, 4, 3, 3, 350000),
        (faculty_ids[1], "38.03.01", "Экономика предприятий и организаций", "Бакалавриат", 120, 200, 12, 12, 12, 390000),
        (faculty_ids[1], "38.03.01", "Международная торговля и логистика", "Бакалавриат", 40, 80, 4, 4, 4, 410000),
        (faculty_ids[1], "38.05.01", "Экономическая безопасность", "Специалитет", 40, 60, 4, 4, 4, 375000),
        (faculty_ids[2], "38.03.01", "Финансы и кредит", "Бакалавриат", 60, 110, 6, 6, 6, 400000),
        (faculty_ids[2], "38.03.01", "Корпоративные финансы и инвестиции", "Бакалавриат", 45, 85, 5, 4, 4, 395000),
        (faculty_ids[3], "38.03.02", "Менеджмент организации", "Бакалавриат", 80, 150, 8, 8, 8, 380000),
        (faculty_ids[3], "43.03.03", "Гостиничное дело", "Бакалавриат", 25, 75, 3, 2, 2, 360000),
        (faculty_ids[3], "38.03.05", "Бизнес-информатика", "Бакалавриат", 35, 65, 4, 3, 3, 375000),
        (faculty_ids[4], "40.03.01", "Юриспруденция", "Бакалавриат", 25, 130, 3, 3, 3, 385000),
        (faculty_ids[4], "38.03.04", "Государственное и муниципальное управление", "Бакалавриат", 30, 90, 3, 3, 3, 370000),
        (faculty_ids[5], "39.03.01", "Социология цифрового общества", "Бакалавриат", 20, 50, 2, 2, 2, 340000),
        (faculty_ids[5], "37.03.01", "Психология управления и бизнеса", "Бакалавриат", 25, 60, 3, 2, 2, 355000),
        (faculty_ids[5], "41.03.04", "Политология и политический анализ", "Бакалавриат", 15, 40, 2, 1, 1, 330000),
        (faculty_ids[6], "42.03.01", "Реклама и связи с общественностью", "Бакалавриат", 30, 140, 3, 3, 3, 420000),
        (faculty_ids[6], "54.03.01", "Дизайн среды и графический дизайн", "Бакалавриат", 15, 65, 2, 1, 1, 410000),
        (faculty_ids[7], "38.05.02", "Таможенное дело", "Специалитет", 30, 100, 3, 3, 3, 365000),
        (faculty_ids[7], "18.03.01", "Химическая технология перспективных материалов", "Бакалавриат", 25, 35, 3, 2, 2, 320000),
        (faculty_ids[8], "01.03.02", "Прикладная математика и Data Science (Форсайт)", "Бакалавриат", 30, 20, 3, 3, 3, 450000),
        (faculty_ids[8], "38.03.01", "Анализ данных и моделирование в экономике", "Бакалавриат", 25, 25, 3, 2, 2, 440000),
        (faculty_ids[9], "42.03.02", "Журналистика и медиаиндустрия", "Бакалавриат", 20, 80, 2, 2, 2, 395000),
        (faculty_ids[9], "42.03.05", "Медиакоммуникации и телепроизводство", "Бакалавриат", 15, 70, 2, 1, 1, 405000),
        (faculty_ids[10], "38.03.02", "Бизнес-администрирование и стартапы", "Бакалавриат", 10, 90, 1, 1, 1, 460000),
        (faculty_ids[10], "38.03.02", "Международный бизнес и управление проектами", "Бакалавриат", 10, 85, 1, 1, 1, 450000)
    ]
    program_ids = []
    for p in programs_data:
        pid = await conn.fetchval(
            """INSERT INTO programs (faculty_id, program_code, name, education_level, budget_places, commercial_places, special_quota, target_quota, separate_quota, annual_tuition_fee)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) RETURNING id""",
            *p
        )
        program_ids.append(pid)

    print("Генерация 800 абитуриентов...")
    applicant_ids = []
    for i in range(1, 801):
        fio = generate_full_name()
        b_year = random.randint(2005, 2008)
        b_date = date(b_year, random.randint(1, 12), random.randint(1, 28))
        snils = generate_snils(i)
        passport = f"{random.randint(4500, 4620)} {random.randint(100000, 999999)}"
        doc_type = random.choice(DOC_TYPES)
        grad_year = random.choice([2024, 2025, 2026])
        school = random.choice(SCHOOLS)
        
        aid = await conn.fetchval(
            """INSERT INTO applicants (snils, full_name, birth_date, passport_number, education_doc_type, doc_issue_year, school_name)
               VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id""",
            snils, fio, b_date, passport, doc_type, grad_year, school
        )
        applicant_ids.append(aid)

    print("Генерация 2000 конкурсных заявлений...")
    app_records = []
    app_counter = 1

    for aid in applicant_ids:
        chosen_programs = random.sample(program_ids, k=random.randint(2, 4))
        for priority, prog_id in enumerate(chosen_programs, start=1):
            if app_counter > 2000:
                break
            year = random.choice([2024, 2025, 2026])
            app_num = f"РЭУ-{year}-{app_counter:05d}"
            app_counter += 1

            form = random.choice(["Очная", "Очно-заочная"])
            basis = random.choice(["Бюджетные места", "Платная основа", "Особая квота", "Целевая квота", "Отдельная квота"])
            quota_type = random.choice(QUOTAS) if basis != "Платная основа" else "Без квот"
            
            math_s = random.randint(55, 100)
            rus_s = random.randint(60, 100)
            choice_sub = random.choice(CHOICE_SUBJECTS)
            choice_s = random.randint(50, 100)
            dvi_s = random.choice([0, 0, 0, random.randint(60, 95)])
            
            ach_title, ach_score = random.choice(ACHIEVEMENTS)
            total_s = math_s + rus_s + choice_s + dvi_s + ach_score

            original = (priority == 1 and random.random() > 0.4)
            consent = original and (random.random() > 0.3)
            
            if total_s >= 265 and original and consent and year < 2026:
                status = "Зачислен"
                order_num = f"ПР-З/{year}-{random.randint(100, 999)}"
                order_date = date(year, 8, random.randint(3, 9))
            elif year == 2026:
                status = random.choice(["Принято", "Участвует в конкурсе", "Ожидает согласия на зачисление"])
                order_num, order_date = None, None
            else:
                status = random.choice(["Участвует в конкурсе", "Отклонено", "Отозвано"])
                order_num, order_date = None, None

            sub_date = date(year, random.randint(6, 7), random.randint(1, 25))

            app_records.append((
                app_num, aid, prog_id, year, priority, form, basis, quota_type,
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

    print("Генерация 600 студентов с ФИО...")
    group_prefixes = ["ПИ-", "ИВТ-", "ПМИ-", "ЭК-", "МЕН-", "ФИН-", "ЮР-", "СОЦ-", "РЕК-", "ТАМ-", "ФОР-", "МЕД-", "ИНТ-"]
    student_records = []

    for i in range(1, 601):
        prog_id = random.choice(program_ids)
        st_name = generate_full_name()
        enroll_year = random.choice([2022, 2023, 2024, 2025])
        course_num = min(2026 - enroll_year + 1, 4)
        study_grp = f"{random.choice(group_prefixes)}{enroll_year % 100}{random.randint(1, 3)}"
        ticket_num = f"СТУД-{enroll_year}-{i:05d}"
        basis = random.choice(["Бюджетная основа", "Договорная основа"])
        status = "Отчислен" if random.random() < 0.05 else ("В академическом отпуске" if random.random() < 0.03 else "Обучается")

        student_records.append((
            prog_id, st_name, ticket_num, study_grp, course_num, enroll_year, basis, status
        ))

    await conn.executemany(
        """INSERT INTO students (program_id, full_name, student_card_number, study_group, study_year, admission_year, education_basis, student_status)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
        student_records
    )

    classrooms_data = []
    buildings_list = ["Корпус 1", "Корпус 2", "Корпус 3", "Корпус 6", "Корпус 8", "Корпус 9"]
    for building in buildings_list:
        for room_num in range(101, 108):
            room_type = random.choice(["Лекционная аудитория", "Компьютерный класс", "Семинарская аудитория", "Лаборатория Data Science"])
            cap = 120 if room_type == "Лекционная аудитория" else (30 if "Компьютерный" in room_type else 45)
            classrooms_data.append((building, f"{room_num}", cap, room_type))

    classroom_ids = []
    for c in classrooms_data:
        cid = await conn.fetchval(
            'INSERT INTO classrooms (building, room_number, capacity, room_type) VALUES ($1, $2, $3, $4) RETURNING id',
            *c
        )
        classroom_ids.append(cid)

    course_names = [
        "Базы данных и аналитика данных", "Алгоритмы и структуры данных", "Микроэкономика",
        "Макроэкономика", "Корпоративные финансы", "Стратегический менеджмент", "Анализ данных на Python",
        "Теория вероятностей и математическая статистика", "Гражданское право", "Бухгалтерский учет и аудит",
        "Машинное обучение в финансовом секторе", "Медиакоммуникации и цифровой PR", "Таможенный контроль",
        "Бизнес-моделирование стартапов", "Цифровая трансформация бизнеса", "Психология деловых переговоров",
        "Информационная безопасность веб-приложений", "Управление проектами в креативных индустриях",
        "Моделирование больших данных (Big Data)", "Международный финансовый рынок", "Дизайн-мышление",
        "Технологии полиграфических материалов"
    ]
    course_ids = []
    for i, c_name in enumerate(course_names):
        tid, dept_id = random.choice(teacher_ids)
        sem = (i % 8) + 1
        cid = await conn.fetchval(
            """INSERT INTO disciplines (department_id, teacher_id, name, semester, academic_hours, control_form)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            dept_id, tid, c_name, sem, random.choice([72, 108, 144]), random.choice(["Экзамен", "Зачет", "Дифференцированный зачет"])
        )
        course_ids.append((cid, sem))

    print("Генерация 1800 экзаменационных оценок...")
    grades_records = []
    student_ids_list = await conn.fetch("SELECT id, student_status FROM students WHERE student_status = 'Обучается'")
    for srow in student_ids_list:
        assigned_courses = random.sample(course_ids, k=min(4, len(course_ids)))
        for cid, sem in assigned_courses:
            pts = random.randint(35, 98)
            is_debt = pts < 50
            letter = "2 (Неуд)" if is_debt else ("5 (Отл)" if pts >= 85 else ("4 (Хор)" if pts >= 70 else "3 (Удовл)"))
            exam_d = date(2026, 1, 15) if sem % 2 == 1 else date(2025, 6, 20)

            grades_records.append((
                srow["id"], cid, sem, pts, letter, is_debt, exam_d
            ))

    await conn.executemany(
        """INSERT INTO grades (student_id, discipline_id, semester, points, grade, has_academic_debt, exam_date)
           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
        grades_records
    )

    print("Генерация 100 записей расписания...")
    schedule_records = []
    slots = ["08:30-10:00", "10:10-11:40", "11:50-13:20", "14:00-15:30", "15:40-17:10"]
    for i in range(100):
        cl_id = random.choice(classroom_ids)
        cid, _ = random.choice(course_ids)
        day = random.randint(1, 6)
        slot = random.choice(slots)
        grp = f"{random.choice(group_prefixes)}23{random.randint(1, 3)}"
        attendees = random.randint(18, 95)
        schedule_records.append((cl_id, cid, day, slot, grp, attendees))

    await conn.executemany(
        """INSERT INTO schedules (classroom_id, discipline_id, day_of_week, time_slot, study_group, attendees_count)
           VALUES ($1, $2, $3, $4, $5, $6)""",
        schedule_records
    )

    await conn.close()
    print("Заполнение базы данных успешно завершено.")

if __name__ == "__main__":
    asyncio.run(seed())