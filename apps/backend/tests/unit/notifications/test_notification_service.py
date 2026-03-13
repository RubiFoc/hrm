"""Unit tests for recipient-scoped in-app notification service behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.employee.dao.onboarding_task_dao import OnboardingTaskDAO
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.notifications.dao.notification_dao import NotificationDAO
from hrm_backend.notifications.models.notification import Notification
from hrm_backend.notifications.services.notification_service import NotificationService
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.models.vacancy import Vacancy


class _AuditServiceStub(AuditService):
    """Audit double that records notification API events in memory."""

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_api_event(self, **kwargs) -> None:  # type: ignore[override]
        """Capture API audit payloads for focused service assertions."""
        self.events.append(kwargs)


def _build_request(path: str, method: str = "GET") -> Request:
    """Create a minimal Starlette request object for service calls."""
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 8000),
        }
    )


def _build_auth_context(*, role: str, subject_id: str) -> AuthContext:
    """Create deterministic auth context for notification tests."""
    return AuthContext(
        subject_id=UUID(subject_id),
        role=role,
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )


def _seed_staff_accounts(session: Session) -> dict[str, str]:
    """Insert manager/accountant fixture accounts used by notification tests."""
    manager_id = "11111111-1111-4111-8111-111111111111"
    accountant_alpha_id = "22222222-2222-4222-8222-222222222222"
    accountant_beta_id = "33333333-3333-4333-8333-333333333333"
    session.add_all(
        [
            StaffAccount(
                staff_id=manager_id,
                login="manager-alpha",
                email="manager@example.com",
                password_hash="hash",
                role="manager",
                is_active=True,
            ),
            StaffAccount(
                staff_id=accountant_alpha_id,
                login="accountant-alpha",
                email="accountant-alpha@example.com",
                password_hash="hash",
                role="accountant",
                is_active=True,
            ),
            StaffAccount(
                staff_id=accountant_beta_id,
                login="accountant-beta",
                email="accountant-beta@example.com",
                password_hash="hash",
                role="accountant",
                is_active=True,
            ),
            StaffAccount(
                staff_id="44444444-4444-4444-8444-444444444444",
                login="hr-user",
                email="hr@example.com",
                password_hash="hash",
                role="hr",
                is_active=True,
            ),
        ]
    )
    session.commit()
    return {
        "manager_id": manager_id,
        "accountant_alpha_id": accountant_alpha_id,
        "accountant_beta_id": accountant_beta_id,
    }


def _seed_manager_workspace_state(
    session: Session,
    *,
    manager_id: str,
) -> tuple[Vacancy, OnboardingTask]:
    """Insert one manager-owned vacancy and one manager-visible onboarding task."""
    vacancy = Vacancy(
        vacancy_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        title="Platform Engineer",
        description="Build platform foundations.",
        department="Engineering",
        status="open",
        hiring_manager_staff_id=manager_id,
        created_at=datetime(2026, 3, 13, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 13, 9, 0, tzinfo=UTC),
    )
    run = OnboardingRun(
        onboarding_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        employee_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        hire_conversion_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        status="started",
        started_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
        started_by_staff_id="44444444-4444-4444-8444-444444444444",
    )
    task = OnboardingTask(
        task_id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        onboarding_id=run.onboarding_id,
        template_id="ffffffff-ffff-4fff-8fff-ffffffffffff",
        template_item_id="12121212-1212-4212-8212-121212121212",
        code="manager_intro",
        title="Manager intro",
        description=None,
        sort_order=10,
        is_required=True,
        status="pending",
        assigned_role="manager",
        assigned_staff_id=None,
        due_at=datetime.now(UTC) - timedelta(days=1),
        completed_at=None,
        created_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 13, 10, 0, tzinfo=UTC),
    )
    session.add_all([vacancy, run, task])
    session.commit()
    return vacancy, task


def test_notification_service_emits_assignment_events_with_role_fanout_and_dedupe() -> None:
    """Verify assignment emitters create one row per recipient and dedupe repeated writes."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    audit_service = _AuditServiceStub()

    with Session(engine) as session:
        staff_ids = _seed_staff_accounts(session)
        vacancy, task = _seed_manager_workspace_state(session, manager_id=staff_ids["manager_id"])
        service = NotificationService(
            notification_dao=NotificationDAO(session=session),
            staff_account_dao=StaffAccountDAO(session=session),
            task_dao=OnboardingTaskDAO(session=session),
            vacancy_dao=VacancyDAO(session=session),
            audit_service=audit_service,
        )
        task.assigned_role = "accountant"
        task.updated_at = datetime(2026, 3, 13, 11, 0, tzinfo=UTC)
        session.flush()

        service.emit_vacancy_assignment_notifications(
            vacancy=vacancy,
            previous_hiring_manager_staff_id=None,
        )
        service.emit_vacancy_assignment_notifications(
            vacancy=vacancy,
            previous_hiring_manager_staff_id=None,
        )
        service.emit_onboarding_task_assignment_notifications(
            task=task,
            employee_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            employee_full_name="Ada Adams",
            previous_assigned_role=None,
            previous_assigned_staff_id=None,
        )
        service.emit_onboarding_task_assignment_notifications(
            task=task,
            employee_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            employee_full_name="Ada Adams",
            previous_assigned_role=None,
            previous_assigned_staff_id=None,
        )
        session.commit()

        notifications = (
            session.query(Notification)
            .order_by(Notification.recipient_staff_id.asc(), Notification.kind.asc())
            .all()
        )

    assert len(notifications) == 3
    assert [notification.kind for notification in notifications] == [
        "vacancy_assignment",
        "onboarding_task_assignment",
        "onboarding_task_assignment",
    ]
    assert notifications[0].recipient_staff_id == staff_ids["manager_id"]
    assert {
        notifications[1].recipient_staff_id,
        notifications[2].recipient_staff_id,
    } == {
        staff_ids["accountant_alpha_id"],
        staff_ids["accountant_beta_id"],
    }


def test_notification_service_list_mark_read_and_digest_are_recipient_scoped() -> None:
    """Verify list/read/digest flows stay recipient-scoped and expose correct counts."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    audit_service = _AuditServiceStub()

    with Session(engine) as session:
        staff_ids = _seed_staff_accounts(session)
        vacancy, task = _seed_manager_workspace_state(session, manager_id=staff_ids["manager_id"])
        service = NotificationService(
            notification_dao=NotificationDAO(session=session),
            staff_account_dao=StaffAccountDAO(session=session),
            task_dao=OnboardingTaskDAO(session=session),
            vacancy_dao=VacancyDAO(session=session),
            audit_service=audit_service,
        )

        service.emit_vacancy_assignment_notifications(
            vacancy=vacancy,
            previous_hiring_manager_staff_id=None,
        )
        session.commit()

        manager_context = _build_auth_context(
            role="manager",
            subject_id=staff_ids["manager_id"],
        )
        accountant_context = _build_auth_context(
            role="accountant",
            subject_id=staff_ids["accountant_alpha_id"],
        )

        list_payload = service.list_notifications(
            auth_context=manager_context,
            request=_build_request("/api/v1/notifications"),
            list_status="unread",
            limit=20,
            offset=0,
        )
        assert list_payload.total == 1
        assert list_payload.unread_count == 1
        assert list_payload.items[0].title == "Vacancy assigned: Platform Engineer"

        digest = service.get_digest(
            auth_context=manager_context,
            request=_build_request("/api/v1/notifications/digest"),
        )
        assert digest.summary.unread_notification_count == 1
        assert digest.summary.active_task_count == 1
        assert digest.summary.overdue_task_count == 1
        assert digest.summary.owned_open_vacancy_count == 1
        assert len(digest.latest_unread_items) == 1

        with pytest.raises(HTTPException) as exc_info:
            service.mark_as_read(
                notification_id=list_payload.items[0].notification_id,
                auth_context=accountant_context,
                request=_build_request(
                    f"/api/v1/notifications/{list_payload.items[0].notification_id}/read",
                    method="POST",
                ),
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "notification_not_found"

        read_payload = service.mark_as_read(
            notification_id=list_payload.items[0].notification_id,
            auth_context=manager_context,
            request=_build_request(
                f"/api/v1/notifications/{list_payload.items[0].notification_id}/read",
                method="POST",
            ),
        )
        assert read_payload.status == "read"

        all_payload = service.list_notifications(
            auth_context=manager_context,
            request=_build_request("/api/v1/notifications?status=all"),
            list_status="all",
            limit=20,
            offset=0,
        )
        assert all_payload.total == 1
        assert all_payload.unread_count == 0
        assert all_payload.items[0].status == "read"

    assert [event["action"] for event in audit_service.events] == [
        "notification:list",
        "notification_digest:read",
        "notification:update",
        "notification:update",
        "notification:list",
    ]
