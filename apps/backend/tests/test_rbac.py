"""Authorization tests for role-permission matrix behavior."""

from fastapi.testclient import TestClient

from hrm_backend.main import app

client = TestClient(app)


def test_missing_role_header_returns_401() -> None:
    """Verify that protected routes require explicit role metadata."""
    response = client.get("/api/v1/vacancies")

    assert response.status_code == 401
    assert "Missing role header" in response.json()["detail"]


def test_unknown_role_returns_403() -> None:
    """Verify that unknown role values are rejected."""
    response = client.get("/api/v1/vacancies", headers={"X-Role": "intern"})

    assert response.status_code == 403
    assert "Unknown role" in response.json()["detail"]


def test_hr_can_create_vacancy() -> None:
    """Verify that HR role has create permission for vacancies."""
    response = client.post("/api/v1/vacancies", headers={"X-Role": "hr"})

    assert response.status_code == 200
    assert response.json() == {"status": "created", "role": "hr"}


def test_candidate_cannot_create_vacancy() -> None:
    """Verify that candidate role is forbidden from vacancy creation."""
    response = client.post("/api/v1/vacancies", headers={"X-Role": "candidate"})

    assert response.status_code == 403
    assert "vacancy:create" in response.json()["detail"]


def test_candidate_can_read_own_profile() -> None:
    """Verify that candidate role can access self profile route."""
    response = client.get("/api/v1/candidate/profile", headers={"X-Role": "candidate"})

    assert response.status_code == 200
    assert response.json() == {"profile": "self", "role": "candidate"}


def test_accountant_can_read_automation_report() -> None:
    """Verify that accountant role has analytics read access."""
    response = client.get("/api/v1/reports/automation", headers={"X-Role": "accountant"})

    assert response.status_code == 200
    assert response.json()["role"] == "accountant"


def test_rbac_matrix_contains_all_phase1_roles() -> None:
    """Verify exported matrix contains the full required role set."""
    response = client.get("/rbac/matrix")

    assert response.status_code == 200
    assert set(response.json()) == {
        "hr",
        "candidate",
        "manager",
        "employee",
        "leader",
        "accountant",
    }
