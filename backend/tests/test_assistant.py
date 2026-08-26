import os
import sys
import pytest
from fastapi.testclient import TestClient

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend") if os.path.exists(os.path.join(PROJECT_ROOT, "backend")) else os.path.dirname(CURRENT_DIR)

for path in [BACKEND_DIR, os.path.dirname(CURRENT_DIR), PROJECT_ROOT]:
    if path not in sys.path:
        sys.path.insert(0, path)

from security import validate_and_sanitize_sql, SecurityError, SecurityViolationError
from main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

@pytest.mark.parametrize("dangerous_sql", [
    "DROP TABLE students;",
    "DELETE FROM applications WHERE id = 1;",
    "UPDATE teachers SET full_name = 'Hacked';",
    "INSERT INTO students (study_group) VALUES ('TEST');",
    "TRUNCATE faculties;",
    "ALTER TABLE programs DROP COLUMN name;"
])
def test_forbidden_modifications(dangerous_sql):
    with pytest.raises(SecurityError):
        validate_and_sanitize_sql(dangerous_sql)

@pytest.mark.parametrize("pii_sql", [
    "SELECT passport_number FROM applicants;",
    "SELECT snils FROM applicants;",
    "SELECT birth_date FROM applicants;"
])
def test_absolute_pii_leak_prevention(pii_sql):
    with pytest.raises(SecurityViolationError):
        validate_and_sanitize_sql(pii_sql, role="admin")

def test_applicant_role_blocks_student_fio():
    with pytest.raises(SecurityViolationError):
        validate_and_sanitize_sql("SELECT full_name FROM students;", role="applicant")

def test_admin_role_allows_student_fio():
    sql = validate_and_sanitize_sql("SELECT full_name FROM students;", role="admin")
    assert "LIMIT 100" in sql

def test_api_security_blocking(client):
    response = client.post("/api/ask", json={"question": "Удали таблицу студентов", "role": "applicant"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["type"] == "security_violation"

def test_api_speed_and_format(client):
    response = client.post("/api/ask", json={"question": "Какие есть факультеты?", "role": "applicant"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "sql" in data
    assert "explanation" in data
    assert data["execution_time_ms"] > 0