"""Unit tests for onboarding task materialization and update semantics."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request

from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.employee.dao.onboarding_run_dao import OnboardingRunDAO
from hrm_backend.employee.dao.onboarding_task_dao import OnboardingTaskDAO
from hrm_backend.employee.dao.onboarding_template_dao import OnboardingTemplateDAO
from hrm_backend.employee.models.onboarding import OnboardingRun
from hrm_backend.employee.models.template import OnboardingTemplate, OnboardingTemplateItem
from hrm_backend.employee.schemas.onboarding import OnboardingTaskUpdateRequest
from hrm_backend.employee.services.onboarding_task_service import OnboardingTaskService


class _UnusedSession:
    """Session double used when transaction methods are not exercised."""


class _UnusedRunDAO:
    """DAO double used when onboarding run persistence is not under test."""


class _UnusedTaskDAO:
    """DAO double used when onboarding task persistence is not under test."""


class _UnusedTemplateDAO:
    """DAO double used when onboarding template persistence is not under test."""


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


def _build_auth_context() -> AuthContext:
    """Create deterministic HR auth context for unit service calls."""
    return AuthContext(
        subject_id=uuid4(),
        role="hr",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )


def _seed_run_and_active_template(session: Session) -> OnboardingRun:
    """Insert one onboarding run plus an active template bundle for task tests."""
    run = OnboardingRun(
        onboarding_id="11111111-1111-4111-8111-111111111111",
        employee_id="22222222-2222-4222-8222-222222222222",
        hire_conversion_id="33333333-3333-4333-8333-333333333333",
        status="started",
        started_by_staff_id="44444444-4444-4444-8444-444444444444",
    )
    template = OnboardingTemplate(
        template_id="55555555-5555-4555-8555-555555555555",
        name="Default onboarding",
        description="Core employee ramp-up checklist.",
        is_active=True,
        created_by_staff_id="66666666-6666-4666-8666-666666666666",
    )
    session.add_all(
        [
            run,
            template,
            OnboardingTemplateItem(
                template_item_id="77777777-7777-4777-8777-777777777777",
                template_id=template.template_id,
                code="accounts",
                title="Create accounts",
                description="Provision required systems",
                sort_order=20,
                is_required=True,
            ),
            OnboardingTemplateItem(
                template_item_id="88888888-8888-4888-8888-888888888888",
                template_id=template.template_id,
                code="intro",
                title="Team intro",
                description=None,
                sort_order=10,
                is_required=False,
            ),
        ]
    )
    session.commit()
    session.refresh(run)
    return run


def test_build_create_payloads_orders_tasks_from_active_template_bundle() -> None:
    """Verify task payload builder maps one active template into deterministic ordered tasks."""
    service = OnboardingTaskService(
        session=_UnusedSession(),  # type: ignore[arg-type]
        run_dao=_UnusedRunDAO(),  # type: ignore[arg-type]
        task_dao=_UnusedTaskDAO(),  # type: ignore[arg-type]
        template_dao=_UnusedTemplateDAO(),  # type: ignore[arg-type]
        audit_service=_AuditServiceStub(),  # type: ignore[arg-type]
    )
    run = OnboardingRun(
        onboarding_id="11111111-1111-4111-8111-111111111111",
        employee_id="22222222-2222-4222-8222-222222222222",
        hire_conversion_id="33333333-3333-4333-8333-333333333333",
        status="started",
        started_by_staff_id="44444444-4444-4444-8444-444444444444",
    )
    template = OnboardingTemplate(
        template_id="55555555-5555-4555-8555-555555555555",
        name="Default onboarding",
        description="Core employee ramp-up checklist.",
        is_active=True,
        created_by_staff_id="66666666-6666-4666-8666-666666666666",
    )

    payloads = service.build_create_payloads(
        onboarding_run=run,
        template=template,
        template_items=[
            OnboardingTemplateItem(
                template_item_id="77777777-7777-4777-8777-777777777777",
                template_id=template.template_id,
                code="accounts",
                title="Create accounts",
                description="Provision required systems",
                sort_order=20,
                is_required=True,
            ),
            OnboardingTemplateItem(
                template_item_id="88888888-8888-4888-8888-888888888888",
                template_id=template.template_id,
                code="intro",
                title="Team intro",
                description=None,
                sort_order=10,
                is_required=False,
            ),
        ],
    )

    assert [payload.code for payload in payloads] == ["intro", "accounts"]
    assert [payload.sort_order for payload in payloads] == [10, 20]
    assert all(str(payload.onboarding_id) == run.onboarding_id for payload in payloads)
    assert all(str(payload.template_id) == template.template_id for payload in payloads)
    assert all(payload.status == "pending" for payload in payloads)


def test_onboarding_task_persistence_enforces_one_generation_per_run() -> None:
    """Verify task generation rejects a second materialization attempt for the same run."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            run = _seed_run_and_active_template(session)
            service = OnboardingTaskService(
                session=session,
                run_dao=OnboardingRunDAO(session=session),
                task_dao=OnboardingTaskDAO(session=session),
                template_dao=OnboardingTemplateDAO(session=session),
                audit_service=_AuditServiceStub(),  # type: ignore[arg-type]
            )

            created = service.create_tasks_from_active_template(onboarding_run=run)
            assert [task.code for task in created] == ["intro", "accounts"]

            with pytest.raises(IntegrityError):
                service.create_tasks_from_active_template(onboarding_run=run)
            session.rollback()
    finally:
        engine.dispose()


def test_update_task_patch_semantics_manage_completion_and_nullable_fields() -> None:
    """Verify task patch semantics set completion time and clear nullable assignment fields."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            run = _seed_run_and_active_template(session)
            service = OnboardingTaskService(
                session=session,
                run_dao=OnboardingRunDAO(session=session),
                task_dao=OnboardingTaskDAO(session=session),
                template_dao=OnboardingTemplateDAO(session=session),
                audit_service=_AuditServiceStub(),  # type: ignore[arg-type]
            )

            created = service.create_tasks_from_active_template(onboarding_run=run)
            task = created[0]

            completed = service.update_task(
                onboarding_id=UUID(run.onboarding_id),
                task_id=UUID(task.task_id),
                payload=OnboardingTaskUpdateRequest(
                    status="completed",
                    assigned_role="hr",
                    assigned_staff_id="99999999-9999-4999-8999-999999999999",
                    due_at=datetime(2026, 4, 2, 9, 0, tzinfo=UTC),
                ),
                auth_context=_build_auth_context(),
                request=_build_request(
                    "PATCH",
                    f"/api/v1/onboarding/runs/{run.onboarding_id}/tasks/{task.task_id}",
                ),
            )
            assert completed.status == "completed"
            assert completed.assigned_role == "hr"
            assert completed.assigned_staff_id is not None
            assert completed.due_at is not None
            assert completed.due_at.replace(tzinfo=UTC) == datetime(
                2026,
                4,
                2,
                9,
                0,
                tzinfo=UTC,
            )
            assert completed.completed_at is not None

            reopened = service.update_task(
                onboarding_id=UUID(run.onboarding_id),
                task_id=UUID(task.task_id),
                payload=OnboardingTaskUpdateRequest(
                    status="in_progress",
                    assigned_role=None,
                    assigned_staff_id=None,
                    due_at=None,
                ),
                auth_context=_build_auth_context(),
                request=_build_request(
                    "PATCH",
                    f"/api/v1/onboarding/runs/{run.onboarding_id}/tasks/{task.task_id}",
                ),
            )
            assert reopened.status == "in_progress"
            assert reopened.assigned_role is None
            assert reopened.assigned_staff_id is None
            assert reopened.due_at is None
            assert reopened.completed_at is None
    finally:
        engine.dispose()
