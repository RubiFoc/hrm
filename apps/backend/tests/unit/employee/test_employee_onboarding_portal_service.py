"""Unit tests for employee self-service onboarding portal behavior."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.dao.onboarding_run_dao import OnboardingRunDAO
from hrm_backend.employee.dao.onboarding_task_dao import OnboardingTaskDAO
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.schemas.onboarding import EmployeeOnboardingTaskUpdateRequest
from hrm_backend.employee.services.employee_onboarding_portal_service import (
    EMPLOYEE_PROFILE_IDENTITY_CONFLICT,
    ONBOARDING_TASK_NOT_ACTIONABLE_BY_EMPLOYEE,
    EmployeeOnboardingPortalService,
)


class _AuditServiceStub:
    """Audit double that captures no-op API event writes."""

    def record_api_event(self, **kwargs) -> None:
        """Ignore audit writes during focused unit tests."""
        del kwargs


def _build_request(method: str, path: str) -> Request:
    """Create minimal Starlette request object for service calls."""
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 8000),
        }
    )


def _build_auth_context(subject_id: str) -> AuthContext:
    """Create deterministic employee auth context for unit portal calls."""
    return AuthContext(
        subject_id=UUID(subject_id),
        role="employee",
        session_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        token_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        expires_at=9999999999,
    )


def _seed_staff_account(session: Session, *, staff_id: str, email: str) -> None:
    """Insert one employee-role staff account row."""
    dao = StaffAccountDAO(session=session)
    dao.create_account(
        login=email,
        email=email,
        password_hash="argon2id$stub",
        role="employee",
        is_active=True,
    )
    account = dao.get_by_identifier(email)
    assert account is not None
    account.staff_id = staff_id
    session.add(account)
    session.commit()


def _seed_employee_portal_bundle(
    session: Session,
    *,
    email: str,
) -> tuple[EmployeeProfile, OnboardingTask]:
    """Insert one employee profile, onboarding run, and actionable/non-actionable tasks."""
    profile = EmployeeProfile(
        employee_id="11111111-1111-4111-8111-111111111111",
        hire_conversion_id="22222222-2222-4222-8222-222222222222",
        vacancy_id="33333333-3333-4333-8333-333333333333",
        candidate_id="44444444-4444-4444-8444-444444444444",
        first_name="Ada",
        last_name="Lovelace",
        email=email,
        phone="+375291234567",
        location="Minsk",
        current_title="Engineer",
        extra_data_json={"languages": ["ru", "en"]},
        offer_terms_summary="Base salary 5000 BYN gross.",
        created_by_staff_id="55555555-5555-4555-8555-555555555555",
    )
    run = OnboardingRun(
        onboarding_id="66666666-6666-4666-8666-666666666666",
        employee_id=profile.employee_id,
        hire_conversion_id=profile.hire_conversion_id,
        status="started",
        started_by_staff_id="77777777-7777-4777-8777-777777777777",
    )
    actionable = OnboardingTask(
        task_id="88888888-8888-4888-8888-888888888888",
        onboarding_id=run.onboarding_id,
        template_id="99999999-9999-4999-8999-999999999999",
        template_item_id="aaaaaaaa-1111-4aaa-8aaa-aaaaaaaaaaaa",
        code="accounts",
        title="Create accounts",
        description="Provision employee systems",
        sort_order=10,
        is_required=True,
        status="pending",
        assigned_role="employee",
        assigned_staff_id=None,
    )
    blocked = OnboardingTask(
        task_id="bbbbbbbb-1111-4bbb-8bbb-bbbbbbbbbbbb",
        onboarding_id=run.onboarding_id,
        template_id="99999999-9999-4999-8999-999999999999",
        template_item_id="cccccccc-1111-4ccc-8ccc-cccccccccccc",
        code="laptop",
        title="Issue laptop",
        description="Handled by HR",
        sort_order=20,
        is_required=True,
        status="pending",
        assigned_role="hr",
        assigned_staff_id=None,
    )
    session.add_all([profile, run, actionable, blocked])
    session.commit()
    session.refresh(profile)
    session.refresh(actionable)
    return profile, actionable


def test_get_portal_links_profile_by_email_and_marks_actionable_tasks() -> None:
    """Verify first self-service read claims staff-account link and returns task actionability."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            staff_id = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
            _seed_staff_account(session, staff_id=staff_id, email="ada@example.com")
            profile, _ = _seed_employee_portal_bundle(session, email="ada@example.com")
            service = EmployeeOnboardingPortalService(
                profile_dao=EmployeeProfileDAO(session=session),
                run_dao=OnboardingRunDAO(session=session),
                task_dao=OnboardingTaskDAO(session=session),
                staff_account_dao=StaffAccountDAO(session=session),
                audit_service=_AuditServiceStub(),  # type: ignore[arg-type]
            )

            response = service.get_portal(
                auth_context=_build_auth_context(staff_id),
                request=_build_request("GET", "/api/v1/employees/me/onboarding"),
            )

            session.refresh(profile)
            assert profile.staff_account_id == staff_id
            assert response.employee_id == UUID(profile.employee_id)
            assert [item.code for item in response.tasks] == ["accounts", "laptop"]
            assert [item.can_update for item in response.tasks] == [True, False]
    finally:
        engine.dispose()


def test_update_task_rejects_non_actionable_employee_assignment_rules() -> None:
    """Verify employee portal rejects updates for tasks assigned to a different role."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            staff_id = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
            _seed_staff_account(session, staff_id=staff_id, email="ada@example.com")
            profile, actionable = _seed_employee_portal_bundle(session, email="ada@example.com")
            service = EmployeeOnboardingPortalService(
                profile_dao=EmployeeProfileDAO(session=session),
                run_dao=OnboardingRunDAO(session=session),
                task_dao=OnboardingTaskDAO(session=session),
                staff_account_dao=StaffAccountDAO(session=session),
                audit_service=_AuditServiceStub(),  # type: ignore[arg-type]
            )

            blocked_task = (
                session.query(OnboardingTask)
                .filter(OnboardingTask.code == "laptop")
                .first()
            )
            assert blocked_task is not None

            with pytest.raises(HTTPException) as exc_info:
                service.update_task(
                    task_id=UUID(blocked_task.task_id),
                    payload=EmployeeOnboardingTaskUpdateRequest(status="completed"),
                    auth_context=_build_auth_context(staff_id),
                    request=_build_request(
                        "PATCH",
                        f"/api/v1/employees/me/onboarding/tasks/{blocked_task.task_id}",
                    ),
                )

            assert exc_info.value.status_code == 409
            assert exc_info.value.detail == ONBOARDING_TASK_NOT_ACTIONABLE_BY_EMPLOYEE

            updated = service.update_task(
                task_id=UUID(actionable.task_id),
                payload=EmployeeOnboardingTaskUpdateRequest(status="completed"),
                auth_context=_build_auth_context(staff_id),
                request=_build_request(
                    "PATCH",
                    f"/api/v1/employees/me/onboarding/tasks/{actionable.task_id}",
                ),
            )
            assert updated.status == "completed"
            assert updated.completed_at is not None

            reopened = service.update_task(
                task_id=UUID(actionable.task_id),
                payload=EmployeeOnboardingTaskUpdateRequest(status="pending"),
                auth_context=_build_auth_context(staff_id),
                request=_build_request(
                    "PATCH",
                    f"/api/v1/employees/me/onboarding/tasks/{actionable.task_id}",
                ),
            )
            assert reopened.status == "pending"
            assert reopened.completed_at is None

            session.refresh(profile)
            assert profile.staff_account_id == staff_id
    finally:
        engine.dispose()


def test_get_portal_rejects_identity_conflict_when_email_matches_multiple_profiles() -> None:
    """Verify e-mail reconciliation fails closed when multiple employee profiles match."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            staff_id = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
            _seed_staff_account(session, staff_id=staff_id, email="shared@example.com")
            _seed_employee_portal_bundle(session, email="shared@example.com")
            session.add(
                EmployeeProfile(
                    employee_id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
                    hire_conversion_id="ffffffff-ffff-4fff-8fff-ffffffffffff",
                    vacancy_id="10101010-1010-4010-8010-101010101010",
                    candidate_id="20202020-2020-4020-8020-202020202020",
                    first_name="Another",
                    last_name="Employee",
                    email="shared@example.com",
                    phone=None,
                    location=None,
                    current_title=None,
                    extra_data_json={},
                    offer_terms_summary=None,
                    created_by_staff_id="55555555-5555-4555-8555-555555555555",
                )
            )
            session.commit()

            service = EmployeeOnboardingPortalService(
                profile_dao=EmployeeProfileDAO(session=session),
                run_dao=OnboardingRunDAO(session=session),
                task_dao=OnboardingTaskDAO(session=session),
                staff_account_dao=StaffAccountDAO(session=session),
                audit_service=_AuditServiceStub(),  # type: ignore[arg-type]
            )

            with pytest.raises(HTTPException) as exc_info:
                service.get_portal(
                    auth_context=_build_auth_context(staff_id),
                    request=_build_request("GET", "/api/v1/employees/me/onboarding"),
                )

            assert exc_info.value.status_code == 409
            assert exc_info.value.detail == EMPLOYEE_PROFILE_IDENTITY_CONFLICT
    finally:
        engine.dispose()
