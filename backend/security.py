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

# Шаблоны поиска чувствительных персональных данных
FORBIDDEN_PII_PATTERNS = [
    r"\bpassport(_number)?\b",
    r"\bsnils\b",
    r"\bbirth_date\b",
    r"\bapplicants\s*\.\s*full_name\b",
    r"\bselect\s+\*\s+from\s+applicants\b",
    r"\bselect\s+.*?\bfull_name\b.*?from\s+applicants\b",
    r"\bselect\s+.*?\bfull_name\b.*?from\s+.*\bapplicants\b"
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
    
    parsed = sqlparse.parse(cleaned_sql)
    if not parsed:
        raise SecurityError("Пустой или некорректный SQL-запрос.")

    for statement in parsed:
        for token in statement.tokens:
            if token.ttype in (Keyword, DML) and token.value.upper() in FORBIDDEN_KEYWORDS:
                raise SecurityError(f"Запрещенная операция модификации: {token.value.upper()}")

    if not cleaned_sql.lower().startswith("select"):
        raise SecurityError("Разрешены исключительно операции чтения (SELECT).")

    used_tables = extract_tables(cleaned_sql)
    invalid_tables = used_tables - ALLOWED_TABLES
    if invalid_tables:
        raise SecurityError(f"Доступ к запрещенным таблицам: {', '.join(invalid_tables)}")

    for pattern in FORBIDDEN_PII_PATTERNS:
        if re.search(pattern, cleaned_sql, re.IGNORECASE):
            raise SecurityError("Запрос заблокирован: обнаружена попытка извлечения персональных данных (ФИО абитуриента, СНИЛС, паспорт).")

    if not re.search(r"\bLIMIT\s+\d+\b", cleaned_sql, re.IGNORECASE):
        cleaned_sql = f"{cleaned_sql} LIMIT {default_limit}"

    return cleaned_sql