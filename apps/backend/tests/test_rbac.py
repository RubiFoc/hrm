"""Authorization unit tests for role-permission matrix behavior."""

import pytest
from fastapi import HTTPException

from hrm_backend.api.rbac_demo import (
    create_vacancy,
    read_automation_report,
    read_own_candidate_profile,
)
from hrm_backend.main import get_rbac_matrix
from hrm_backend.rbac import parse_role, require_permission


def test_parse_role_missing_value_returns_401() -> None:
    """Verify that empty role claim is rejected as unauthorized."""
    with pytest.raises(HTTPException) as exc_info:
        parse_role(None)

    assert exc_info.value.status_code == 401
    assert "Missing role claim" in str(exc_info.value.detail)


def test_parse_role_unknown_value_returns_403() -> None:
    """Verify that unknown role claim is rejected as forbidden."""
    with pytest.raises(HTTPException) as exc_info:
        parse_role("intern")

    assert exc_info.value.status_code == 403
    assert "Unknown role claim" in str(exc_info.value.detail)


def test_hr_can_create_vacancy() -> None:
    """Verify that HR role has create permission for vacancies."""
    response = create_vacancy(role="hr")

    assert response == {"status": "created", "role": "hr"}


def test_candidate_cannot_create_vacancy() -> None:
    """Verify permission dependency blocks candidate from vacancy creation."""
    dependency = require_permission("vacancy:create")

    with pytest.raises(HTTPException) as exc_info:
        dependency(role="candidate")

    assert exc_info.value.status_code == 403
    assert "vacancy:create" in str(exc_info.value.detail)


def test_candidate_can_read_own_profile() -> None:
    """Verify candidate role can access own profile endpoint function."""
    response = read_own_candidate_profile(role="candidate")

    assert response == {"profile": "self", "role": "candidate"}


def test_accountant_can_read_automation_report() -> None:
    """Verify accountant role has analytics read access."""
    response = read_automation_report(role="accountant")

    assert response["role"] == "accountant"


def test_rbac_matrix_contains_all_phase1_roles() -> None:
    """Verify exported RBAC matrix includes full phase-1 role set."""
    matrix = get_rbac_matrix()

    assert set(matrix) == {
        "hr",
        "candidate",
        "manager",
        "employee",
        "leader",
        "accountant",
    }
