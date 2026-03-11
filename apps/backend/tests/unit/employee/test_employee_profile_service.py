"""Unit tests for employee profile bootstrap payload mapping."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.services.employee_profile_service import EmployeeProfileService


class _UnusedHireConversionDAO:
    """DAO double used when only payload construction is under test."""


class _UnusedEmployeeProfileDAO:
    """DAO double used when only payload construction is under test."""


class _UnusedOnboardingRunService:
    """Service double used when onboarding persistence is not under test."""


class _UnusedOnboardingTaskService:
    """Service double used when onboarding task persistence is not under test."""


class _UnusedAuditService:
    """Audit double used when no audit writes are expected."""


class _UnusedSession:
    """Session double used when transaction methods are not exercised."""


def _build_service() -> EmployeeProfileService:
    """Create employee profile service with inert dependencies for unit tests."""
    return EmployeeProfileService(
        session=_UnusedSession(),  # type: ignore[arg-type]
        hire_conversion_dao=_UnusedHireConversionDAO(),  # type: ignore[arg-type]
        profile_dao=_UnusedEmployeeProfileDAO(),  # type: ignore[arg-type]
        onboarding_service=_UnusedOnboardingRunService(),  # type: ignore[arg-type]
        onboarding_task_service=_UnusedOnboardingTaskService(),  # type: ignore[arg-type]
        audit_service=_UnusedAuditService(),  # type: ignore[arg-type]
    )


def test_build_create_payload_maps_ready_hire_conversion_to_employee_profile() -> None:
    """Verify employee profile payload is built deterministically from frozen snapshots."""
    service = _build_service()
    conversion = HireConversion(
        conversion_id="11111111-1111-4111-8111-111111111111",
        vacancy_id="22222222-2222-4222-8222-222222222222",
        candidate_id="33333333-3333-4333-8333-333333333333",
        offer_id="44444444-4444-4444-8444-444444444444",
        hired_transition_id="55555555-5555-4555-8555-555555555555",
        status="ready",
        candidate_snapshot_json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "phone": "+375291234567",
            "location": "Minsk",
            "current_title": "Backend Engineer",
            "extra_data": {"languages": ["ru", "en"]},
        },
        offer_snapshot_json={
            "status": "accepted",
            "terms_summary": "Base salary 5000 BYN gross.",
            "proposed_start_date": "2026-04-01",
            "expires_at": "2026-03-20",
            "note": "Manual delivery by HR.",
            "sent_at": "2026-03-10T10:30:00Z",
            "sent_by_staff_id": "66666666-6666-4666-8666-666666666666",
            "decision_at": "2026-03-10T12:00:00Z",
            "decision_note": "Accepted by phone.",
            "decision_recorded_by_staff_id": "77777777-7777-4777-8777-777777777777",
        },
        converted_by_staff_id="88888888-8888-4888-8888-888888888888",
    )

    payload = service.build_create_payload(
        conversion=conversion,
        created_by_staff_id="99999999-9999-4999-8999-999999999999",
    )

    assert str(payload.hire_conversion_id) == conversion.conversion_id
    assert str(payload.vacancy_id) == conversion.vacancy_id
    assert str(payload.candidate_id) == conversion.candidate_id
    assert payload.first_name == "Ada"
    assert payload.last_name == "Lovelace"
    assert payload.email == "ada@example.com"
    assert payload.phone == "+375291234567"
    assert payload.location == "Minsk"
    assert payload.current_title == "Backend Engineer"
    assert payload.extra_data == {"languages": ["ru", "en"]}
    assert payload.offer_terms_summary == "Base salary 5000 BYN gross."
    assert payload.start_date == date(2026, 4, 1)


def test_build_create_payload_rejects_invalid_hire_conversion_snapshot() -> None:
    """Verify malformed frozen snapshot data is rejected before profile persistence."""
    service = _build_service()
    conversion = HireConversion(
        conversion_id="11111111-1111-4111-8111-111111111111",
        vacancy_id="22222222-2222-4222-8222-222222222222",
        candidate_id="33333333-3333-4333-8333-333333333333",
        offer_id="44444444-4444-4444-8444-444444444444",
        hired_transition_id="55555555-5555-4555-8555-555555555555",
        status="ready",
        candidate_snapshot_json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            # Missing `email` must fail validation.
            "extra_data": {},
        },
        offer_snapshot_json={
            "status": "accepted",
            "terms_summary": None,
        },
        converted_by_staff_id="88888888-8888-4888-8888-888888888888",
    )

    with pytest.raises(ValidationError):
        service.build_create_payload(
            conversion=conversion,
            created_by_staff_id="99999999-9999-4999-8999-999999999999",
        )
