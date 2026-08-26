import re
import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML

ALLOWED_TABLES = {
    "faculties", "departments", "teachers", "programs",
    "applicants", "applications", "students", "classrooms",
    "disciplines", "grades", "schedules"
}

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "GRANT", "REVOKE", "CREATE", "EXEC", "EXECUTE", "MERGE", "CALL"
}

ABSOLUTE_FORBIDDEN_PII = [
    r"\bpassport(_number)?\b",
    r"\bsnils\b",
    r"\bbirth_date\b"
]

APPLICANT_RESTRICTED_PATTERNS = [
    r"\bapplicants\s*\.\s*full_name\b",
    r"\bstudents\s*\.\s*full_name\b",
    r"\bselect\s+\*\s+from\s+applicants\b",
    r"\bselect\s+.*?\bfull_name\b.*?from\s+applicants\b",
    r"\bselect\s+.*?\bfull_name\b.*?from\s+students\b"
]

# Расширенный фильтр деструктивных глаголов и модификаций данных
DANGEROUS_INTENT_PATTERNS = [
    r"\b(drop|delete|truncate|alter|insert|update|create|grant|revoke)\b",
    r"\b(удали|удалить|сотри|стереть|очисти|очистить|дропни|дропнуть)\b",
    r"\b(добавь|добавить|вставь|вставить|создай|создать|запиши|записать)\b",
    r"\b(обнови|обновить|измени|изменить|поменяй|поменять|исправь|исправить)\b",
    r"\b(паспорт|паспорта|снилс|паспортные)\b"
]

class SecurityError(Exception):
    pass

class SecurityViolationError(SecurityError):
    pass

class UnrecognizedQueryError(SecurityError):
    pass

def check_prompt_security_intent(user_text: str):
    text_lower = user_text.lower()
    for pattern in DANGEROUS_INTENT_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            if any(w in text_lower for w in ["паспорт", "снилс"]):
                raise SecurityViolationError("Запрос заблокирован: обнаружена попытка извлечения персональных данных (паспорт/СНИЛС).")
            raise SecurityViolationError("Запрещенная операция модификации: СУБД работает в режиме строгого чтения (SELECT ONLY).")

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
                        real_name = identifier.get_real_name()
                        if real_name:
                            tables.add(real_name.lower())
                elif isinstance(token, Identifier):
                    real_name = token.get_real_name()
                    if real_name:
                        tables.add(real_name.lower())
                elif token.ttype is Keyword:
                    from_seen = False
    return tables

def validate_and_sanitize_sql(sql: str, role: str = "applicant", default_limit: int = 100) -> str:
    cleaned_sql = sql.strip().rstrip(";")
    if not cleaned_sql:
        return ""

    parsed = sqlparse.parse(cleaned_sql)
    if not parsed:
        raise UnrecognizedQueryError("Не удалось распознать структуру запроса.")

    for statement in parsed:
        for token in statement.tokens:
            if token.ttype in (Keyword, DML) and token.value.upper() in FORBIDDEN_KEYWORDS:
                raise SecurityViolationError(f"Запрещенная операция модификации: {token.value.upper()}")

    # Разрешаем запросы, начинающиеся с SELECT или WITH (CTE)
    sql_start = cleaned_sql.lower()
    if not (sql_start.startswith("select") or sql_start.startswith("with")):
        raise SecurityViolationError("Разрешены исключительно операции чтения (SELECT / WITH).")

    for pattern in ABSOLUTE_FORBIDDEN_PII:
        if re.search(pattern, cleaned_sql, re.IGNORECASE):
            raise SecurityViolationError("Запрос заблокирован: паспортные данные и СНИЛС защищены политикой конфиденциальности.")

    # Ролевые ограничения для абитуриента
    if role in ("applicant", "guest"):
        for pattern in APPLICANT_RESTRICTED_PATTERNS:
            if re.search(pattern, cleaned_sql, re.IGNORECASE):
                raise SecurityViolationError(f"Для роли '{role}' вывод персональных данных обучающихся запрещен.")

        # Блокировка сырых оценок студентов (без агрегации)
        if "grades" in cleaned_sql.lower():
            has_aggregate = any(fn in cleaned_sql.upper() for fn in ("COUNT(", "AVG(", "SUM(", "MIN(", "MAX("))
            if not has_aggregate:
                raise SecurityViolationError("Для роли 'Абитуриент' доступ к журналу оценок разрешен только в агрегированном виде (средний балл, статистика).")

    used_tables = extract_tables(cleaned_sql)
    invalid_tables = used_tables - ALLOWED_TABLES
    if invalid_tables:
        raise UnrecognizedQueryError(f"Сущности '{', '.join(invalid_tables)}' не найдены в базе данных университета.")

    if not re.search(r"\bLIMIT\s+\d+\b", cleaned_sql, re.IGNORECASE):
        cleaned_sql = f"{cleaned_sql} LIMIT {default_limit}"

    return cleaned_sql