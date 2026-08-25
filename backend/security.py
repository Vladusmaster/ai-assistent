import re
import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML

ALLOWED_TABLES = {
    "faculties", "departments", "teachers", "programs",
    "applications", "students", "classrooms", "courses",
    "grades", "classroom_schedules"
}

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "GRANT", "REVOKE", "CREATE", "EXEC", "EXECUTE", "MERGE"
}

FORBIDDEN_STUDENT_PII_PATTERNS = [
    r"\bpassport\b", r"\bphone\b", r"\bemail\b.*student", r"\bfull_name\b.*student"
]

class SecurityError(Exception):
    pass

def extract_tables(sql: str) -> set:
    parsed = sqlparse.parse(sql)
    tables = set()
    for statement in parsed:
        from_seen = False
        for token in statement.tokens:
            if token.is_keyword and token.value.upper() in ("FROM", "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN"):
                from_seen = True
                continue
            if from_seen:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        tables.add(identifier.get_real_name().lower())
                elif isinstance(token, Identifier):
                    tables.add(token.get_real_name().lower())
                elif token.ttype is Keyword:
                    from_seen = False
    return {t for t in tables if t}

def validate_and_sanitize_sql(sql: str, default_limit: int = 100) -> str:
    cleaned_sql = sql.strip().rstrip(";")
    
    # 1. Проверка на запрещенные команды
    parsed = sqlparse.parse(cleaned_sql)
    for statement in parsed:
        for token in statement.tokens:
            if token.ttype in (Keyword, DML) and token.value.upper() in FORBIDDEN_KEYWORDS:
                raise SecurityError(f"Запрещенная операция: {token.value.upper()}")

    # 2. Проверка, что запрос начинается строго с SELECT
    if not cleaned_sql.lower().startswith("select"):
        raise SecurityError("Разрешены только SELECT-запросы.")

    # 3. Валидация таблиц по whitelist
    used_tables = extract_tables(cleaned_sql)
    invalid_tables = used_tables - ALLOWED_TABLES
    if invalid_tables:
        raise SecurityError(f"Доступ к таблицам запрещен: {', '.join(invalid_tables)}")

    # 4. Проверка на персональные данные
    for pattern in FORBIDDEN_STUDENT_PII_PATTERNS:
        if re.search(pattern, cleaned_sql, re.IGNORECASE):
            raise SecurityError("Запрос нарушает политику конфиденциальности персональных данных.")

    # 5. Автоматическое добавление LIMIT
    if not re.search(r"\bLIMIT\s+\d+\b", cleaned_sql, re.IGNORECASE):
        cleaned_sql = f"{cleaned_sql} LIMIT {default_limit}"

    return cleaned_sql