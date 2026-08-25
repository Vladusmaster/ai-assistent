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
DROP TABLE IF EXISTS classroom_schedules CASCADE;
DROP TABLE IF EXISTS grades CASCADE;
DROP TABLE IF EXISTS student_courses CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS classrooms CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS applications CASCADE;
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
    contact_email VARCHAR(100) NOT NULL
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
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    degree_level VARCHAR(50) NOT NULL,
    budget_places INT NOT NULL DEFAULT 0,
    paid_places INT NOT NULL DEFAULT 0,
    tuition_fee_per_year INT NOT NULL DEFAULT 0
);

CREATE TABLE applications (
    id SERIAL PRIMARY KEY,
    program_id INT NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    application_number VARCHAR(64) NOT NULL UNIQUE,
    year INT NOT NULL,
    math_score INT NOT NULL,
    russian_score INT NOT NULL,
    special_score INT NOT NULL,
    total_score INT NOT NULL,
    education_form VARCHAR(50) NOT NULL,
    education_basis VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    submission_date DATE NOT NULL
);

CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    program_id INT NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    student_ticket_number VARCHAR(64) NOT NULL UNIQUE,
    study_group VARCHAR(50) NOT NULL,
    course_year INT NOT NULL,
    enrollment_year INT NOT NULL,
    education_basis VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL
);

CREATE TABLE classrooms (
    id SERIAL PRIMARY KEY,
    building VARCHAR(50) NOT NULL,
    room_number VARCHAR(20) NOT NULL,
    capacity INT NOT NULL,
    room_type VARCHAR(50) NOT NULL
);

CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    department_id INT NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    teacher_id INT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    semester INT NOT NULL,
    total_hours INT NOT NULL,
    control_type VARCHAR(50) NOT NULL
);

CREATE TABLE grades (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id INT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    semester INT NOT NULL,
    grade_points INT NOT NULL,
    letter_grade VARCHAR(5) NOT NULL,
    is_debt BOOLEAN NOT NULL DEFAULT FALSE,
    exam_date DATE NOT NULL
);

CREATE TABLE classroom_schedules (
    id SERIAL PRIMARY KEY,
    classroom_id INT NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    course_id INT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
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

def generate_full_name():
    if random.random() > 0.5:
        return f"{random.choice(LAST_NAMES_M)} {random.choice(FIRST_NAMES_M)} {random.choice(PATRONYMICS_M)}"
    return f"{random.choice(LAST_NAMES_F)} {random.choice(FIRST_NAMES_F)} {random.choice(PATRONYMICS_F)}"

async def seed():
    print(f"Подключение к БД {DB_NAME} на {DB_HOST}:{DB_PORT} под пользователем {DB_USER}...")
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
        ("Высшая школа кибертехнологий, математики и статистики", "ВШ КМиС", "Тихомиров Николай Петрович", "Корпус 3 (Стремянный пер., 36)", "cyber@rea.ru"),
        ("Высшая школа экономики и бизнеса", "ВШЭиБ", "Гришин Виктор Иванович", "Корпус 1 (Стремянный пер., 28)", "vsheb@rea.ru"),
        ("Высшая школа менеджмента", "ВШМ", "Пономарев Максим Александрович", "Корпус 6 (Зацепа, 41)", "vshm@rea.ru"),
        ("Высшая школа финансов", "ВШФ", "Слепов Владимир Александрович", "Корпус 2 (Стремянный пер., 28с1)", "vshf@rea.ru"),
        ("Высшая школа права", "ВШП", "Экимов Алик Исмаилович", "Корпус 8 (Зацепа, 43)", "law@rea.ru")
    ]
    faculty_ids = []
    for f in faculties_data:
        fid = await conn.fetchval(
            "INSERT INTO faculties (name, short_name, dean_full_name, building, contact_email) VALUES ($1, $2, $3, $4, $5) RETURNING id",
            *f
        )
        faculty_ids.append(fid)

    departments_data = [
        (faculty_ids[0], "Кафедра прикладной информатики и информационной безопасности", "Сухоруков Андрей Сергеевич"),
        (faculty_ids[0], "Кафедра математических методов в экономике", "Зайцев Владимир Кириллович"),
        (faculty_ids[0], "Кафедра статистики и анализа данных", "Карманов Михаил Владимирович"),
        (faculty_ids[1], "Кафедра экономической теории", "Устюжанина Елена Владимировна"),
        (faculty_ids[1], "Кафедра мировой экономики", "Хасбулатов Руслан Имранович"),
        (faculty_ids[2], "Кафедра общего и стратегического менеджмента", "Сидоров Олег Николаевич"),
        (faculty_ids[2], "Кафедра маркетинга", "Скоробогатых Ирина Ивановна"),
        (faculty_ids[3], "Кафедра банковского дела и монетарного регулирования", "Горохова Диана Викторовна"),
        (faculty_ids[3], "Кафедра финансового контроля и аудита", "Прокофьев Станислав Евгеньевич"),
        (faculty_ids[4], "Кафедра гражданско-правовых дисциплин", "Курбанов Рашад Афатович")
    ]
    department_ids = []
    for d in departments_data:
        did = await conn.fetchval(
            "INSERT INTO departments (faculty_id, name, head_full_name) VALUES ($1, $2, $3) RETURNING id",
            *d
        )
        department_ids.append(did)

    degrees = ["д.э.н.", "д.т.н.", "к.э.н.", "к.т.н.", "к.ф.-м.н.", "к.ю.н."]
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
        (faculty_ids[0], "09.03.03", "Прикладная информатика в экономике", "Бакалавриат", 50, 70, 360000),
        (faculty_ids[0], "09.03.01", "Информатика и вычислительная техника", "Бакалавриат", 45, 55, 370000),
        (faculty_ids[0], "01.03.02", "Прикладная математика и информатика", "Бакалавриат", 35, 40, 350000),
        (faculty_ids[1], "38.03.01", "Экономика", "Бакалавриат", 120, 200, 390000),
        (faculty_ids[1], "38.03.01", "Международная торговля и логистика", "Бакалавриат", 40, 80, 410000),
        (faculty_ids[2], "38.03.02", "Менеджмент", "Бакалавриат", 80, 150, 380000),
        (faculty_ids[2], "38.03.02", "Маркетинг и цифровые коммуникации", "Бакалавриат", 30, 90, 390000),
        (faculty_ids[3], "38.03.01", "Финансы и кредит", "Бакалавриат", 60, 110, 400000),
        (faculty_ids[3], "38.05.01", "Экономическая безопасность", "Специалитет", 40, 60, 375000),
        (faculty_ids[4], "40.03.01", "Юриспруденция", "Бакалавриат", 25, 130, 385000)
    ]
    program_ids = []
    for p in programs_data:
        pid = await conn.fetchval(
            """INSERT INTO programs (faculty_id, code, name, degree_level, budget_places, paid_places, tuition_fee_per_year)
               VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id""",
            *p
        )
        program_ids.append(pid)

    classrooms_data = []
    for building in ["Корпус 1", "Корпус 2", "Корпус 3", "Корпус 6", "Корпус 8"]:
        for room_num in range(101, 108):
            room_type = random.choice(["Лекционная аудитория", "Компьютерный класс", "Семинарская аудитория"])
            cap = 120 if room_type == "Лекционная аудитория" else (30 if room_type == "Компьютерный класс" else 45)
            classrooms_data.append((building, f"{room_num}", cap, room_type))

    classroom_ids = []
    for c in classrooms_data:
        cid = await conn.fetchval(
            "INSERT INTO classrooms (building, room_number, capacity, room_type) VALUES ($1, $2, $3, $4) RETURNING id",
            *c
        )
        classroom_ids.append(cid)

    course_names = [
        "Базы данных и проектирование ИС", "Алгоритмы и структуры данных", "Микроэкономика",
        "Макроэкономика", "Корпоративные финансы", "Стратегический менеджмент", "Анализ данных на Python",
        "Теория вероятностей и математическая статистика", "Гражданское право", "Бухгалтерский учет и аудит",
        "Машинное обучение в финансовом секторе", "Операционные системы"
    ]
    course_ids = []
    for i, c_name in enumerate(course_names):
        tid, dept_id = random.choice(teacher_ids)
        sem = (i % 8) + 1
        cid = await conn.fetchval(
            """INSERT INTO courses (department_id, teacher_id, name, semester, total_hours, control_type)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            dept_id, tid, c_name, sem, random.choice([72, 108, 144]), random.choice(["Экзамен", "Зачет", "Дифференцированный зачет"])
        )
        course_ids.append((cid, sem))

    print("Генерация 1000 заявлений абитуриентов...")
    app_records = []
    statuses = ["Подано", "В конкурсе", "Зачислен", "Отозвано", "Отклонено"]
    forms = ["Очная", "Очно-заочная"]
    bases = ["Бюджет", "Договор"]

    for i in range(1, 1001):
        prog_id = random.choice(program_ids)
        year = random.choice([2022, 2023, 2024, 2025, 2026])
        math_s = random.randint(55, 100)
        rus_s = random.randint(60, 100)
        spec_s = random.randint(50, 100)
        total_s = math_s + rus_s + spec_s + random.choice([0, 2, 5, 10])
        app_num = f"ABIT-{year}-{i:05d}"
        b_type = random.choice(bases)
        st = "Зачислен" if (total_s > 250 and random.random() > 0.4) else random.choice(statuses)
        sub_date = date(year, random.randint(6, 8), random.randint(1, 25))

        app_records.append((
            prog_id, app_num, year, math_s, rus_s, spec_s, total_s,
            random.choice(forms), b_type, st, sub_date
        ))

    await conn.executemany(
        """INSERT INTO applications (program_id, application_number, year, math_score, russian_score, special_score, total_score, education_form, education_basis, status, submission_date)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
        app_records
    )

    print("Генерация 500 студентов...")
    student_records = []
    student_ids_list = []
    group_prefixes = ["ПИ-", "ИВТ-", "ПМИ-", "ЭК-", "МЕН-", "ФИН-", "ЮР-"]

    for i in range(1, 501):
        prog_id = random.choice(program_ids)
        enroll_year = random.choice([2021, 2022, 2023, 2024, 2025])
        course_num = min(2026 - enroll_year + 1, 4)
        study_grp = f"{random.choice(group_prefixes)}{enroll_year % 100}{random.randint(1, 4)}"
        ticket_num = f"STU-{enroll_year}-{i:05d}"
        basis = random.choice(["Бюджет", "Договор"])
        status = "Отчислен" if random.random() < 0.08 else ("В академическом отпуске" if random.random() < 0.04 else "Обучается")

        sid = await conn.fetchval(
            """INSERT INTO students (program_id, student_ticket_number, study_group, course_year, enrollment_year, education_basis, status)
               VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id""",
            prog_id, ticket_num, study_grp, course_num, enroll_year, basis, status
        )
        student_ids_list.append((sid, course_num, status))

    print("Генерация 1200 оценок...")
    grades_records = []
    active_students = [s for s in student_ids_list if s[2] == "Обучается"]
    for sid, c_year, _ in active_students:
        assigned_courses = random.sample(course_ids, k=min(3, len(course_ids)))
        for cid, sem in assigned_courses:
            pts = random.randint(35, 98)
            is_debt = pts < 50
            letter = "2" if is_debt else ("5" if pts >= 85 else ("4" if pts >= 70 else "3"))
            exam_d = date(2026, 1, 15) if sem % 2 == 1 else date(2025, 6, 20)

            grades_records.append((
                sid, cid, sem, pts, letter, is_debt, exam_d
            ))

    await conn.executemany(
        """INSERT INTO grades (student_id, course_id, semester, grade_points, letter_grade, is_debt, exam_date)
           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
        grades_records
    )

    print("Генерация расписания аудиторного фонда...")
    schedule_records = []
    slots = ["08:30-10:00", "10:10-11:40", "11:50-13:20", "14:00-15:30", "15:40-17:10"]
    for cid, _ in course_ids:
        cl_id = random.choice(classroom_ids)
        day = random.randint(1, 6)
        slot = random.choice(slots)
        grp = f"{random.choice(group_prefixes)}23{random.randint(1, 3)}"
        attendees = random.randint(18, 95)
        schedule_records.append((cl_id, cid, day, slot, grp, attendees))

    await conn.executemany(
        """INSERT INTO classroom_schedules (classroom_id, course_id, day_of_week, time_slot, study_group, attendees_count)
           VALUES ($1, $2, $3, $4, $5, $6)""",
        schedule_records
    )

    total_rows = await conn.fetchval("""
        SELECT (SELECT count(*) FROM faculties) +
               (SELECT count(*) FROM departments) +
               (SELECT count(*) FROM teachers) +
               (SELECT count(*) FROM programs) +
               (SELECT count(*) FROM classrooms) +
               (SELECT count(*) FROM courses) +
               (SELECT count(*) FROM applications) +
               (SELECT count(*) FROM students) +
               (SELECT count(*) FROM grades) +
               (SELECT count(*) FROM classroom_schedules);
    """)

    await conn.close()
    print(f"База данных успешно заполнена. Всего записей: {total_rows}")

if __name__ == "__main__":
    asyncio.run(seed())