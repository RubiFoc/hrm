"""Authorization unit tests for role-permission matrix behavior."""

import pytest
from fastapi import HTTPException

from hrm_backend.api.rbac_demo import (
    create_vacancy,
    read_automation_report,
    read_own_candidate_profile,
)
from hrm_backend.main import get_rbac_matrix
from hrm_backend.rbac import (
    BackgroundAccessDeniedError,
    enforce_background_permission,
    evaluate_permission,
    parse_role,
)


class _InMemoryAuditService:
    """Simple audit service stub for background enforcement tests."""

    def __init__(self) -> None:
        """Initialize in-memory event sink."""
        self.events: list[dict[str, object]] = []

    def record_permission_decision(self, **payload: object) -> None:
        """Capture permission decision payload."""
        self.events.append(payload)


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


def test_candidate_is_denied_for_vacancy_create_permission() -> None:
    """Verify centralized evaluator denies vacancy create for candidate role."""
    decision = evaluate_permission(role="candidate", permission="vacancy:create")

    assert decision.allowed is False
    assert decision.reason is not None
    assert "vacancy:create" in decision.reason


def test_background_enforcement_records_denied_decision() -> None:
    """Verify background permission check denies and records audit decision."""
    audit_service = _InMemoryAuditService()

    with pytest.raises(BackgroundAccessDeniedError):
        enforce_background_permission(
            subject_id="job-user",
            role="candidate",
            permission="vacancy:create",
            audit_service=audit_service,  # type: ignore[arg-type]
            correlation_id="job-correlation-1",
        )

    assert len(audit_service.events) == 1
    assert audit_service.events[0]["allowed"] is False
    assert audit_service.events[0]["permission"] == "vacancy:create"
    assert audit_service.events[0]["correlation_id"] == "job-correlation-1"


def test_background_enforcement_records_invalid_role_reason() -> None:
    """Verify invalid background role produces explicit audit deny reason."""
    audit_service = _InMemoryAuditService()

    with pytest.raises(BackgroundAccessDeniedError):
        enforce_background_permission(
            subject_id="job-user",
            role="intern",
            permission="vacancy:create",
            audit_service=audit_service,  # type: ignore[arg-type]
            correlation_id="job-correlation-2",
        )

    assert len(audit_service.events) == 1
    assert audit_service.events[0]["allowed"] is False
    assert audit_service.events[0]["reason"] == "Unknown role claim: intern"


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
