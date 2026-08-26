import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from security import validate_and_sanitize_sql, SecurityError
from main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

# 1. Модульные тесты безопасности SQL
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

# 2. Модульные тесты защиты ПДн
@pytest.mark.parametrize("pii_sql", [
    "SELECT passport_number FROM applicants;",
    "SELECT snils, full_name FROM applicants;",
    "SELECT * FROM applicants;",
    "SELECT applicants.full_name, score_russian FROM applicants JOIN applications ON applicants.id = applications.applicant_id;"
])
def test_pii_leak_prevention(pii_sql):
    with pytest.raises(SecurityError):
        validate_and_sanitize_sql(pii_sql)

# 3. Интеграционные тесты API
def test_api_security_blocking(client):
    response = client.post("/api/ask", json={"question": "Удали таблицу студентов"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["type"] == "security_violation"

def test_api_speed_and_format(client):
    response = client.post("/api/ask", json={"question": "Какие есть факультеты?"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "sql" in data
    assert "explanation" in data
    assert "data" in data
    assert data["execution_time_ms"] > 0