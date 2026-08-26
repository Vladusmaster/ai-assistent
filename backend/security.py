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

FORBIDDEN_PII_PATTERNS = [
    r"\bpassport(_number)?\b",
    r"\bsnils\b",
    r"\bbirth_date\b",
    r"\bapplicants\s*\.\s*full_name\b",
    r"\bselect\s+\*\s+from\s+applicants\b",
    r"\bselect\s+.*?\bfull_name\b.*?from\s+applicants\b",
    r"\bselect\s+.*?\bfull_name\b.*?from\s+.*\bapplicants\b"
]

# Проверка деструктивных намерений в естественном тексте запроса
DANGEROUS_INTENT_PATTERNS = [
    r"\b(drop|delete|truncate|alter|insert|update)\b",
    r"\b(удали|удалить|стереть|очисти|дропни|измени|вставь)\b",
    r"\b(паспорт|паспорта|снилс|паспортные)\b"
]

class SecurityError(Exception):
    """Базовое исключение безопасности."""
    pass

class SecurityViolationError(SecurityError):
    """Настоящая угроза: SQL-инъекция, DDL/DML или попытка кражи ПДн."""
    pass

class UnrecognizedQueryError(SecurityError):
    """Случайный ввод или опечатка в имени таблицы."""
    pass

def check_prompt_security_intent(user_text: str):
    """Проверяет прямой текст пользователя на деструктивные команды и попытки взлома."""
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

def validate_and_sanitize_sql(sql: str, default_limit: int = 100) -> str:
    cleaned_sql = sql.strip().rstrip(";")
    if not cleaned_sql:
        return ""

    parsed = sqlparse.parse(cleaned_sql)
    if not parsed:
        raise UnrecognizedQueryError("Не удалось распознать структуру запроса.")

    # 1. Проверка DML/DDL операций
    for statement in parsed:
        for token in statement.tokens:
            if token.ttype in (Keyword, DML) and token.value.upper() in FORBIDDEN_KEYWORDS:
                raise SecurityViolationError(f"Запрещенная операция модификации данных: {token.value.upper()}")

    # 2. Проверка, что запрос начинается строго с SELECT
    if not cleaned_sql.lower().startswith("select"):
        raise SecurityViolationError("Разрешены исключительно операции чтения (SELECT).")

    # 3. Проверка утечки ПДн
    for pattern in FORBIDDEN_PII_PATTERNS:
        if re.search(pattern, cleaned_sql, re.IGNORECASE):
            raise SecurityViolationError("Запрос заблокирован: обнаружена попытка извлечения персональных данных абитуриентов.")

    # 4. Проверка белого списка таблиц
    used_tables = extract_tables(cleaned_sql)
    invalid_tables = used_tables - ALLOWED_TABLES
    if invalid_tables:
        raise UnrecognizedQueryError(f"Сущности '{', '.join(invalid_tables)}' не найдены в базе данных университета.")

    # 5. Автоматический LIMIT
    if not re.search(r"\bLIMIT\s+\d+\b", cleaned_sql, re.IGNORECASE):
        cleaned_sql = f"{cleaned_sql} LIMIT {default_limit}"

    return cleaned_sql