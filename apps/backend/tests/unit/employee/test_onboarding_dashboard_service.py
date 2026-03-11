"""Unit tests for onboarding dashboard visibility and aggregation logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.dao.onboarding_run_dao import OnboardingRunDAO
from hrm_backend.employee.dao.onboarding_task_dao import OnboardingTaskDAO
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.services.onboarding_dashboard_service import (
    ONBOARDING_RUN_NOT_FOUND,
    OnboardingDashboardService,
)


class _AuditServiceStub:
    """Audit double used for focused onboarding dashboard tests."""

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


def _build_auth_context(role: str, subject_id: str) -> AuthContext:
    """Create deterministic auth context for dashboard tests."""
    return AuthContext(
        subject_id=UUID(subject_id),
        role=role,
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )


def _seed_dashboard_records(session: Session) -> tuple[str, str, str]:
    """Insert employee profiles, onboarding runs, and materialized tasks for dashboard tests."""
    manager_subject_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    session.add_all(
        [
            EmployeeProfile(
                employee_id="11111111-1111-4111-8111-111111111111",
                hire_conversion_id="22222222-2222-4222-8222-222222222222",
                vacancy_id="33333333-3333-4333-8333-333333333333",
                candidate_id="44444444-4444-4444-8444-444444444444",
                first_name="Ada",
                last_name="Lovelace",
                email="ada@example.com",
                phone=None,
                location="Minsk",
                current_title="Engineer",
                extra_data_json={},
                offer_terms_summary="Laptop and access baseline.",
                start_date=datetime(2026, 4, 1, tzinfo=UTC).date(),
                created_by_staff_id="55555555-5555-4555-8555-555555555555",
            ),
            EmployeeProfile(
                employee_id="66666666-6666-4666-8666-666666666666",
                hire_conversion_id="77777777-7777-4777-8777-777777777777",
                vacancy_id="88888888-8888-4888-8888-888888888888",
                candidate_id="99999999-9999-4999-8999-999999999999",
                first_name="Grace",
                last_name="Hopper",
                email="grace@example.com",
                phone=None,
                location="Brest",
                current_title="Engineering Manager",
                extra_data_json={},
                offer_terms_summary="Manager onboarding plan.",
                start_date=datetime(2026, 4, 15, tzinfo=UTC).date(),
                created_by_staff_id="10101010-1010-4010-8010-101010101010",
            ),
        ]
    )
    session.add_all(
        [
            OnboardingRun(
                onboarding_id="12121212-1212-4212-8212-121212121212",
                employee_id="11111111-1111-4111-8111-111111111111",
                hire_conversion_id="22222222-2222-4222-8222-222222222222",
                status="started",
                started_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
                started_by_staff_id="13131313-1313-4313-8313-131313131313",
            ),
            OnboardingRun(
                onboarding_id="14141414-1414-4414-8414-141414141414",
                employee_id="66666666-6666-4666-8666-666666666666",
                hire_conversion_id="77777777-7777-4777-8777-777777777777",
                status="started",
                started_at=datetime(2026, 3, 11, 9, 0, tzinfo=UTC),
                started_by_staff_id="15151515-1515-4515-8515-151515151515",
            ),
        ]
    )
    session.add_all(
        [
            OnboardingTask(
                task_id="16161616-1616-4616-8616-161616161616",
                onboarding_id="12121212-1212-4212-8212-121212121212",
                template_id="17171717-1717-4717-8717-171717171717",
                template_item_id="18181818-1818-4818-8818-181818181818",
                code="manager_intro",
                title="Manager intro",
                description="Meet your manager",
                sort_order=10,
                is_required=True,
                status="in_progress",
                assigned_role="manager",
                assigned_staff_id=None,
                due_at=datetime.now(UTC) - timedelta(days=1),
                completed_at=None,
            ),
            OnboardingTask(
                task_id="19191919-1919-4919-8919-191919191919",
                onboarding_id="12121212-1212-4212-8212-121212121212",
                template_id="17171717-1717-4717-8717-171717171717",
                template_item_id="20202020-2020-4020-8020-202020202020",
                code="employee_docs",
                title="Upload documents",
                description=None,
                sort_order=20,
                is_required=True,
                status="completed",
                assigned_role="employee",
                assigned_staff_id=None,
                due_at=None,
                completed_at=datetime.now(UTC) - timedelta(hours=4),
            ),
            OnboardingTask(
                task_id="21212121-2121-4212-8212-212121212121",
                onboarding_id="14141414-1414-4414-8414-141414141414",
                template_id="22222222-2222-4222-8222-222222222222",
                template_item_id="23232323-2323-4232-8232-232323232323",
                code="hr_briefing",
                title="HR briefing",
                description="Review policy baseline",
                sort_order=10,
                is_required=True,
                status="pending",
                assigned_role="hr",
                assigned_staff_id=manager_subject_id,
                due_at=datetime.now(UTC) + timedelta(days=2),
                completed_at=None,
            ),
        ]
    )
    session.commit()
    return (
        manager_subject_id,
        "12121212-1212-4212-8212-121212121212",
        "14141414-1414-4414-8414-141414141414",
    )


def test_dashboard_service_filters_manager_visible_runs_and_aggregates_counts() -> None:
    """Verify manager visibility is limited to runs with manager-role or direct assignments."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            manager_subject_id, visible_run_id, direct_assignment_run_id = _seed_dashboard_records(
                session
            )
            service = OnboardingDashboardService(
                profile_dao=EmployeeProfileDAO(session=session),
                run_dao=OnboardingRunDAO(session=session),
                task_dao=OnboardingTaskDAO(session=session),
                audit_service=_AuditServiceStub(),  # type: ignore[arg-type]
            )

            response = service.list_runs(
                auth_context=_build_auth_context("manager", manager_subject_id),
                request=_build_request("GET", "/api/v1/onboarding/runs"),
                search=None,
                task_status=None,
                assigned_role=None,
                assigned_staff_id=None,
                overdue_only=False,
                limit=20,
                offset=0,
            )

            assert response.total == 2
            assert [str(item.onboarding_id) for item in response.items] == [
                visible_run_id,
                direct_assignment_run_id,
            ]
            assert response.summary.run_count == 2
            assert response.summary.total_tasks == 3
            assert response.summary.overdue_tasks == 1
            assert response.items[0].progress_percent == 50
            assert response.items[1].progress_percent == 0
    finally:
        engine.dispose()


def test_dashboard_service_applies_filters_and_blocks_invisible_run_detail() -> None:
    """Verify HR filters work and manager cannot read onboarding detail outside assignment scope."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            manager_subject_id, visible_run_id, direct_assignment_run_id = _seed_dashboard_records(
                session
            )
            service = OnboardingDashboardService(
                profile_dao=EmployeeProfileDAO(session=session),
                run_dao=OnboardingRunDAO(session=session),
                task_dao=OnboardingTaskDAO(session=session),
                audit_service=_AuditServiceStub(),  # type: ignore[arg-type]
            )

            filtered = service.list_runs(
                auth_context=_build_auth_context(
                    "hr",
                    "24242424-2424-4242-8242-242424242424",
                ),
                request=_build_request("GET", "/api/v1/onboarding/runs"),
                search="ada",
                task_status="in_progress",
                assigned_role="manager",
                assigned_staff_id=None,
                overdue_only=True,
                limit=20,
                offset=0,
            )
            assert filtered.total == 1
            assert str(filtered.items[0].onboarding_id) == visible_run_id

            detail = service.get_run(
                onboarding_id=UUID(visible_run_id),
                auth_context=_build_auth_context("manager", manager_subject_id),
                request=_build_request("GET", f"/api/v1/onboarding/runs/{visible_run_id}"),
            )
            assert detail.first_name == "Ada"
            assert [task.code for task in detail.tasks] == ["manager_intro", "employee_docs"]

            with pytest.raises(HTTPException) as exc_info:
                service.get_run(
                    onboarding_id=UUID(direct_assignment_run_id),
                    auth_context=_build_auth_context(
                        "manager",
                        "25252525-2525-4252-8252-252525252525",
                    ),
                    request=_build_request(
                        "GET",
                        f"/api/v1/onboarding/runs/{direct_assignment_run_id}",
                    ),
                )
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == ONBOARDING_RUN_NOT_FOUND
    finally:
        engine.dispose()
