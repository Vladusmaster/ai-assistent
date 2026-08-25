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
DROP TABLE IF EXISTS "расписание" CASCADE;
DROP TABLE IF EXISTS "оценки" CASCADE;
DROP TABLE IF EXISTS "дисциплины" CASCADE;
DROP TABLE IF EXISTS "аудитории" CASCADE;
DROP TABLE IF EXISTS "студенты" CASCADE;
DROP TABLE IF EXISTS "заявления" CASCADE;
DROP TABLE IF EXISTS "абитуриенты" CASCADE;
DROP TABLE IF EXISTS "направления" CASCADE;
DROP TABLE IF EXISTS "преподаватели" CASCADE;
DROP TABLE IF EXISTS "кафедры" CASCADE;
DROP TABLE IF EXISTS "факультеты" CASCADE;

CREATE TABLE "факультеты" (
    "id" SERIAL PRIMARY KEY,
    "название" VARCHAR(255) NOT NULL UNIQUE,
    "сокращение" VARCHAR(50) NOT NULL,
    "декан_фио" VARCHAR(255) NOT NULL,
    "корпус" VARCHAR(100) NOT NULL,
    "электронная_почта" VARCHAR(100) NOT NULL
);

CREATE TABLE "кафедры" (
    "id" SERIAL PRIMARY KEY,
    "факультет_id" INT NOT NULL REFERENCES "факультеты"("id") ON DELETE CASCADE,
    "название" VARCHAR(255) NOT NULL,
    "заведующий_фио" VARCHAR(255) NOT NULL
);

CREATE TABLE "преподаватели" (
    "id" SERIAL PRIMARY KEY,
    "кафедра_id" INT NOT NULL REFERENCES "кафедры"("id") ON DELETE CASCADE,
    "фио" VARCHAR(255) NOT NULL,
    "ученая_степень" VARCHAR(100) NOT NULL,
    "ученое_звание" VARCHAR(100) NOT NULL,
    "должность" VARCHAR(100) NOT NULL,
    "электронная_почта" VARCHAR(100) NOT NULL
);

CREATE TABLE "направления" (
    "id" SERIAL PRIMARY KEY,
    "факультет_id" INT NOT NULL REFERENCES "факультеты"("id") ON DELETE CASCADE,
    "код_направления" VARCHAR(20) NOT NULL,
    "название" VARCHAR(255) NOT NULL,
    "уровень_образования" VARCHAR(50) NOT NULL,
    "бюджетные_места" INT NOT NULL DEFAULT 0,
    "платные_места" INT NOT NULL DEFAULT 0,
    "квота_особая" INT NOT NULL DEFAULT 0,
    "квота_целевая" INT NOT NULL DEFAULT 0,
    "квота_отдельная" INT NOT NULL DEFAULT 0,
    "стоимость_обучения_год" INT NOT NULL DEFAULT 0
);

CREATE TABLE "абитуриенты" (
    "id" SERIAL PRIMARY KEY,
    "снилс" VARCHAR(14) NOT NULL UNIQUE,
    "фио" VARCHAR(255) NOT NULL,
    "дата_рождения" DATE NOT NULL,
    "паспорт_серия_номер" VARCHAR(20) NOT NULL,
    "тип_документа_образования" VARCHAR(100) NOT NULL,
    "год_выдачи_документа" INT NOT NULL,
    "учебное_заведение" VARCHAR(255) NOT NULL
);

CREATE TABLE "заявления" (
    "id" SERIAL PRIMARY KEY,
    "номер_заявления" VARCHAR(64) NOT NULL UNIQUE,
    "абитуриент_id" INT NOT NULL REFERENCES "абитуриенты"("id") ON DELETE CASCADE,
    "направление_id" INT NOT NULL REFERENCES "направления"("id") ON DELETE CASCADE,
    "год_кампании" INT NOT NULL,
    "приоритет" INT NOT NULL,
    "форма_обучения" VARCHAR(50) NOT NULL,
    "основание_поступления" VARCHAR(100) NOT NULL,
    "вид_квоты" VARCHAR(100) NOT NULL DEFAULT 'Без квот',
    "балл_русский_язык" INT NOT NULL,
    "балл_математика" INT NOT NULL,
    "предмет_по_выбору" VARCHAR(100) NOT NULL,
    "балл_предмет_по_выбору" INT NOT NULL,
    "балл_дви" INT NOT NULL DEFAULT 0,
    "баллы_индивидуальных_достижений" INT NOT NULL DEFAULT 0,
    "вид_индивидуального_достижения" VARCHAR(200) NOT NULL DEFAULT 'Нет',
    "сумма_баллов" INT NOT NULL,
    "подан_оригинал" BOOLEAN NOT NULL DEFAULT FALSE,
    "подано_согласие" BOOLEAN NOT NULL DEFAULT FALSE,
    "статус" VARCHAR(100) NOT NULL,
    "номер_приказа_зачисления" VARCHAR(100),
    "дата_приказа" DATE,
    "дата_подачи" DATE NOT NULL
);

CREATE TABLE "студенты" (
    "id" SERIAL PRIMARY KEY,
    "направление_id" INT NOT NULL REFERENCES "направления"("id") ON DELETE CASCADE,
    "номер_студбилета" VARCHAR(64) NOT NULL UNIQUE,
    "учебная_группа" VARCHAR(50) NOT NULL,
    "курс" INT NOT NULL,
    "год_поступления" INT NOT NULL,
    "основание_обучения" VARCHAR(50) NOT NULL,
    "статус_студента" VARCHAR(50) NOT NULL
);

CREATE TABLE "аудитории" (
    "id" SERIAL PRIMARY KEY,
    "корпус" VARCHAR(50) NOT NULL,
    "номер_аудитории" VARCHAR(20) NOT NULL,
    "вместимость" INT NOT NULL,
    "тип_аудитории" VARCHAR(50) NOT NULL
);

CREATE TABLE "дисциплины" (
    "id" SERIAL PRIMARY KEY,
    "кафедра_id" INT NOT NULL REFERENCES "кафедры"("id") ON DELETE CASCADE,
    "преподаватель_id" INT NOT NULL REFERENCES "преподаватели"("id") ON DELETE CASCADE,
    "название" VARCHAR(255) NOT NULL,
    "семестр" INT NOT NULL,
    "академические_часы" INT NOT NULL,
    "форма_контроля" VARCHAR(50) NOT NULL
);

CREATE TABLE "оценки" (
    "id" SERIAL PRIMARY KEY,
    "студент_id" INT NOT NULL REFERENCES "студенты"("id") ON DELETE CASCADE,
    "дисциплина_id" INT NOT NULL REFERENCES "дисциплины"("id") ON DELETE CASCADE,
    "семестр" INT NOT NULL,
    "баллы" INT NOT NULL,
    "оценка" VARCHAR(20) NOT NULL,
    "академическая_задолженность" BOOLEAN NOT NULL DEFAULT FALSE,
    "дата_экзамена" DATE NOT NULL
);

CREATE TABLE "расписание" (
    "id" SERIAL PRIMARY KEY,
    "аудитория_id" INT NOT NULL REFERENCES "аудитории"("id") ON DELETE CASCADE,
    "дисциплина_id" INT NOT NULL REFERENCES "дисциплины"("id") ON DELETE CASCADE,
    "день_недели" INT NOT NULL,
    "временной_слот" VARCHAR(50) NOT NULL,
    "учебная_группа" VARCHAR(50) NOT NULL,
    "количество_слушателей" INT NOT NULL
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
    print(f"Подключение к базе данных {DB_NAME} на {DB_HOST}:{DB_PORT}...")
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
            'INSERT INTO "факультеты" ("название", "сокращение", "декан_фио", "корпус", "электронная_почта") VALUES ($1, $2, $3, $4, $5) RETURNING id',
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
            'INSERT INTO "кафедры" ("факультет_id", "название", "заведующий_фио") VALUES ($1, $2, $3) RETURNING id',
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
                """INSERT INTO "преподаватели" ("кафедра_id", "фио", "ученая_степень", "ученое_звание", "должность", "электронная_почта")
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
            """INSERT INTO "направления" ("факультет_id", "код_направления", "название", "уровень_образования", "бюджетные_места", "платные_места", "квота_особая", "квота_целевая", "квота_отдельная", "стоимость_обучения_год")
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
            """INSERT INTO "абитуриенты" ("снилс", "фио", "дата_рождения", "паспорт_серия_номер", "тип_документа_образования", "год_выдачи_документа", "учебное_заведение")
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
        """INSERT INTO "заявления" (
            "номер_заявления", "абитуриент_id", "направление_id", "год_кампании", "приоритет",
            "форма_обучения", "основание_поступления", "вид_квоты", "балл_русский_язык",
            "балл_математика", "предмет_по_выбору", "балл_предмет_по_выбору", "балл_дви",
            "баллы_индивидуальных_достижений", "вид_индивидуального_достижения", "сумма_баллов",
            "подан_оригинал", "подано_согласие", "статус", "номер_приказа_зачисления",
            "дата_приказа", "дата_подачи"
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)""",
        app_records
    )

    print("Генерация 600 студентов...")
    student_records = []
    group_prefixes = ["ПИ-", "ИВТ-", "ПМИ-", "ЭК-", "МЕН-", "ФИН-", "ЮР-", "СОЦ-", "РЕК-", "ТАМ-", "ФОР-", "МЕД-", "ИНТ-"]
    student_ids_list = []

    for i in range(1, 601):
        prog_id = random.choice(program_ids)
        enroll_year = random.choice([2022, 2023, 2024, 2025])
        course_num = min(2026 - enroll_year + 1, 4)
        study_grp = f"{random.choice(group_prefixes)}{enroll_year % 100}{random.randint(1, 3)}"
        ticket_num = f"СТУД-{enroll_year}-{i:05d}"
        basis = random.choice(["Бюджетная основа", "Договорная основа"])
        status = "Отчислен" if random.random() < 0.05 else ("В академическом отпуске" if random.random() < 0.03 else "Обучается")

        sid = await conn.fetchval(
            """INSERT INTO "студенты" ("направление_id", "номер_студбилета", "учебная_группа", "курс", "год_поступления", "основание_обучения", "статус_студента")
               VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id""",
            prog_id, ticket_num, study_grp, course_num, enroll_year, basis, status
        )
        student_ids_list.append((sid, course_num, status))

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
            'INSERT INTO "аудитории" ("корпус", "номер_аудитории", "вместимость", "тип_аудитории") VALUES ($1, $2, $3, $4) RETURNING id',
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
            """INSERT INTO "дисциплины" ("кафедра_id", "преподаватель_id", "название", "семестр", "академические_часы", "форма_контроля")
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            dept_id, tid, c_name, sem, random.choice([72, 108, 144]), random.choice(["Экзамен", "Зачет", "Дифференцированный зачет"])
        )
        course_ids.append((cid, sem))

    print("Генерация 1800 экзаменационных оценок...")
    grades_records = []
    active_students = [s for s in student_ids_list if s[2] == "Обучается"]
    for sid, c_year, _ in active_students:
        assigned_courses = random.sample(course_ids, k=min(4, len(course_ids)))
        for cid, sem in assigned_courses:
            pts = random.randint(35, 98)
            is_debt = pts < 50
            letter = "2 (Неуд)" if is_debt else ("5 (Отл)" if pts >= 85 else ("4 (Хор)" if pts >= 70 else "3 (Удовл)"))
            exam_d = date(2026, 1, 15) if sem % 2 == 1 else date(2025, 6, 20)

            grades_records.append((
                sid, cid, sem, pts, letter, is_debt, exam_d
            ))

    await conn.executemany(
        """INSERT INTO "оценки" ("студент_id", "дисциплина_id", "семестр", "баллы", "оценка", "академическая_задолженность", "дата_экзамена")
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
        """INSERT INTO "расписание" ("аудитория_id", "дисциплина_id", "день_недели", "временной_слот", "учебная_группа", "количество_слушателей")
           VALUES ($1, $2, $3, $4, $5, $6)""",
        schedule_records
    )

    counts = {
        "факультеты": await conn.fetchval('SELECT count(*) FROM "факультеты"'),
        "кафедры": await conn.fetchval('SELECT count(*) FROM "кафедры"'),
        "преподаватели": await conn.fetchval('SELECT count(*) FROM "преподаватели"'),
        "направления": await conn.fetchval('SELECT count(*) FROM "направления"'),
        "абитуриенты": await conn.fetchval('SELECT count(*) FROM "абитуриенты"'),
        "заявления": await conn.fetchval('SELECT count(*) FROM "заявления"'),
        "студенты": await conn.fetchval('SELECT count(*) FROM "студенты"'),
        "аудитории": await conn.fetchval('SELECT count(*) FROM "аудитории"'),
        "дисциплины": await conn.fetchval('SELECT count(*) FROM "дисциплины"'),
        "оценки": await conn.fetchval('SELECT count(*) FROM "оценки"'),
        "расписание": await conn.fetchval('SELECT count(*) FROM "расписание"')
    }

    total_rows = sum(counts.values())
    await conn.close()
    
    print("\n--- Итог заполнения базы данных ---")
    for tbl, cnt in counts.items():
        print(f"  {tbl}: {cnt}")
    print(f"Всего строк в БД: {total_rows}")

if __name__ == "__main__":
    asyncio.run(seed())