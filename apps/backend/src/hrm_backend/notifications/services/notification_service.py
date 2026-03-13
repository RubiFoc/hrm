"""Business service for in-app notifications and on-demand digests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.employee.dao.onboarding_task_dao import OnboardingTaskDAO
from hrm_backend.employee.models.onboarding import OnboardingTask
from hrm_backend.employee.utils.onboarding import ONBOARDING_TASK_STATUS_COMPLETED
from hrm_backend.notifications.dao.notification_dao import NotificationDAO
from hrm_backend.notifications.models.notification import Notification
from hrm_backend.notifications.schemas.notification import (
    NotificationCreate,
    NotificationDigestResponse,
    NotificationDigestSummaryResponse,
    NotificationListResponse,
    NotificationPayload,
    NotificationResponse,
)
from hrm_backend.notifications.utils.notifications import (
    DIGEST_UNREAD_LIMIT,
    NOTIFICATION_KIND_ONBOARDING_TASK_ASSIGNMENT,
    NOTIFICATION_KIND_VACANCY_ASSIGNMENT,
    is_notifiable_recipient_role,
    resolve_notification_status,
)
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.models.vacancy import Vacancy

NOTIFICATION_NOT_FOUND = "notification_not_found"


class NotificationService:
    """Read, update, and emit recipient-scoped in-app notifications."""

    def __init__(
        self,
        *,
        notification_dao: NotificationDAO,
        staff_account_dao: StaffAccountDAO,
        task_dao: OnboardingTaskDAO,
        vacancy_dao: VacancyDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize notification service dependencies.

        Args:
            notification_dao: DAO for notification persistence and reads.
            staff_account_dao: DAO for role/staff recipient resolution.
            task_dao: DAO for task counts used in digest computation.
            vacancy_dao: DAO for manager-owned vacancy counts used in digests.
            audit_service: Audit service for protected notification API reads and updates.
        """
        self._notification_dao = notification_dao
        self._staff_account_dao = staff_account_dao
        self._task_dao = task_dao
        self._vacancy_dao = vacancy_dao
        self._audit_service = audit_service

    def list_notifications(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
        list_status: str,
        limit: int,
        offset: int,
    ) -> NotificationListResponse:
        """List notifications that belong only to the current authenticated recipient."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        unread_only = list_status == "unread"
        items = self._notification_dao.list_for_recipient(
            recipient_staff_id=actor_sub,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )
        unread_count = self._notification_dao.count_unread_for_recipient(
            recipient_staff_id=actor_sub,
        )
        total = (
            unread_count
            if unread_only
            else self._notification_dao.count_all_for_recipient(recipient_staff_id=actor_sub)
        )
        self._audit_service.record_api_event(
            action="notification:list",
            resource_type="notification",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
        )
        return NotificationListResponse(
            items=[_to_notification_response(entity) for entity in items],
            total=total,
            limit=limit,
            offset=offset,
            unread_count=unread_count,
        )

    def mark_as_read(
        self,
        *,
        notification_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> NotificationResponse:
        """Mark one recipient-owned notification as read."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        entity = self._notification_dao.get_by_id_for_recipient(
            notification_id=str(notification_id),
            recipient_staff_id=actor_sub,
        )
        if entity is None:
            self._audit_service.record_api_event(
                action="notification:update",
                resource_type="notification",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=str(notification_id),
                reason=NOTIFICATION_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=NOTIFICATION_NOT_FOUND,
            )

        if entity.read_at is None:
            entity.read_at = datetime.now(UTC)
            entity = self._notification_dao.mark_as_read(entity=entity)

        self._audit_service.record_api_event(
            action="notification:update",
            resource_type="notification",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.notification_id,
        )
        return _to_notification_response(entity)

    def get_digest(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
    ) -> NotificationDigestResponse:
        """Build an on-demand digest for the current authenticated recipient."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        unread_count = self._notification_dao.count_unread_for_recipient(
            recipient_staff_id=actor_sub,
        )
        latest_unread = self._notification_dao.list_for_recipient(
            recipient_staff_id=actor_sub,
            unread_only=True,
            limit=DIGEST_UNREAD_LIMIT,
            offset=0,
        )
        assigned_tasks = self._task_dao.list_visible_to_actor(
            actor_role=actor_role,
            actor_staff_id=actor_sub,
        )
        active_tasks = [
            task for task in assigned_tasks if task.status != ONBOARDING_TASK_STATUS_COMPLETED
        ]
        now = datetime.now(UTC)
        owned_open_vacancy_count = 0
        if actor_role == "manager":
            owned_open_vacancy_count = sum(
                1
                for vacancy in self._vacancy_dao.list_by_hiring_manager_staff_id(actor_sub)
                if vacancy.status == "open"
            )

        summary = NotificationDigestSummaryResponse(
            unread_notification_count=unread_count,
            active_task_count=len(active_tasks),
            overdue_task_count=sum(
                1
                for task in active_tasks
                if task.due_at is not None and _normalize_datetime(task.due_at) < now
            ),
            owned_open_vacancy_count=owned_open_vacancy_count,
        )
        self._audit_service.record_api_event(
            action="notification_digest:read",
            resource_type="notification",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
        )
        return NotificationDigestResponse(
            generated_at=now,
            summary=summary,
            latest_unread_items=[_to_notification_response(entity) for entity in latest_unread],
        )

    def emit_vacancy_assignment_notifications(
        self,
        *,
        vacancy: Vacancy,
        previous_hiring_manager_staff_id: str | None,
    ) -> None:
        """Emit a manager notification when vacancy ownership changes to a new recipient."""
        new_accounts = self._resolve_direct_recipient_accounts(vacancy.hiring_manager_staff_id)
        previous_recipient_ids = {
            account.staff_id
            for account in self._resolve_direct_recipient_accounts(previous_hiring_manager_staff_id)
        }
        if not new_accounts:
            return

        payloads = [
            NotificationCreate(
                recipient_staff_id=UUID(account.staff_id),
                recipient_role=account.role,
                kind=NOTIFICATION_KIND_VACANCY_ASSIGNMENT,
                source_type="vacancy",
                source_id=UUID(vacancy.vacancy_id),
                dedupe_key=_build_event_dedupe_key(
                    kind=NOTIFICATION_KIND_VACANCY_ASSIGNMENT,
                    source_id=vacancy.vacancy_id,
                    event_time=_normalize_datetime(vacancy.updated_at),
                ),
                title=f"Vacancy assigned: {vacancy.title}",
                body=(
                    f"You were assigned as the hiring manager for {vacancy.title} "
                    f"in {vacancy.department}."
                ),
                payload=NotificationPayload(
                    vacancy_id=UUID(vacancy.vacancy_id),
                    vacancy_title=vacancy.title,
                ),
            )
            for account in new_accounts
            if account.staff_id not in previous_recipient_ids
        ]
        self._notification_dao.create_notifications(payloads=payloads, commit=False)

    def emit_onboarding_task_assignment_notifications(
        self,
        *,
        task: OnboardingTask,
        employee_id: str,
        employee_full_name: str,
        previous_assigned_role: str | None,
        previous_assigned_staff_id: str | None,
    ) -> None:
        """Emit manager/accountant notifications when task assignment visibility changes."""
        new_accounts = self._resolve_assignment_recipient_accounts(
            assigned_role=task.assigned_role,
            assigned_staff_id=task.assigned_staff_id,
        )
        previous_recipient_ids = {
            account.staff_id
            for account in self._resolve_assignment_recipient_accounts(
                assigned_role=previous_assigned_role,
                assigned_staff_id=previous_assigned_staff_id,
            )
        }
        if not new_accounts:
            return

        payloads = [
            NotificationCreate(
                recipient_staff_id=UUID(account.staff_id),
                recipient_role=account.role,
                kind=NOTIFICATION_KIND_ONBOARDING_TASK_ASSIGNMENT,
                source_type="onboarding_task",
                source_id=UUID(task.task_id),
                dedupe_key=_build_event_dedupe_key(
                    kind=NOTIFICATION_KIND_ONBOARDING_TASK_ASSIGNMENT,
                    source_id=task.task_id,
                    event_time=_normalize_datetime(task.updated_at),
                ),
                title=f"Onboarding task assigned: {task.title}",
                body=_build_task_assignment_body(
                    employee_full_name=employee_full_name,
                    task_title=task.title,
                    due_at=task.due_at,
                ),
                payload=NotificationPayload(
                    onboarding_id=UUID(task.onboarding_id),
                    task_id=UUID(task.task_id),
                    employee_id=UUID(employee_id),
                    employee_full_name=employee_full_name,
                    task_title=task.title,
                    due_at=task.due_at,
                ),
            )
            for account in new_accounts
            if account.staff_id not in previous_recipient_ids
        ]
        self._notification_dao.create_notifications(payloads=payloads, commit=False)

    def _resolve_direct_recipient_accounts(self, staff_id: str | None) -> list[StaffAccount]:
        """Resolve a single staff subject to an active v1 notification recipient if possible."""
        if staff_id is None:
            return []
        account = self._staff_account_dao.get_by_id(staff_id)
        if (
            account is None
            or not account.is_active
            or not is_notifiable_recipient_role(account.role)
        ):
            return []
        return [account]

    def _resolve_assignment_recipient_accounts(
        self,
        *,
        assigned_role: str | None,
        assigned_staff_id: str | None,
    ) -> list[StaffAccount]:
        """Resolve all manager/accountant recipients implied by one task assignment state."""
        recipients: dict[str, StaffAccount] = {}
        if assigned_role is not None and is_notifiable_recipient_role(assigned_role):
            for account in self._staff_account_dao.list_active_by_role(assigned_role):
                recipients[account.staff_id] = account

        for account in self._resolve_direct_recipient_accounts(assigned_staff_id):
            recipients[account.staff_id] = account

        return list(recipients.values())


def _to_notification_response(entity: Notification) -> NotificationResponse:
    """Map one notification ORM entity to the public response schema."""
    return NotificationResponse(
        notification_id=UUID(entity.notification_id),
        recipient_staff_id=UUID(entity.recipient_staff_id),
        recipient_role=entity.recipient_role,
        kind=entity.kind,
        source_type=entity.source_type,
        source_id=UUID(entity.source_id),
        status=resolve_notification_status(entity.read_at),
        title=entity.title,
        body=entity.body,
        payload=NotificationPayload.model_validate(entity.payload_json),
        created_at=_normalize_datetime(entity.created_at),
        read_at=_normalize_datetime(entity.read_at),
    )


def _normalize_datetime(value: datetime | None) -> datetime | None:
    """Normalize persisted datetimes to timezone-aware UTC values."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _build_event_dedupe_key(*, kind: str, source_id: str, event_time: datetime | None) -> str:
    """Build a deterministic dedupe key for one emitted notification event."""
    suffix = "unknown"
    if event_time is not None:
        suffix = event_time.astimezone(UTC).isoformat()
    return f"{kind}:{source_id}:{suffix}"


def _build_task_assignment_body(
    *,
    employee_full_name: str,
    task_title: str,
    due_at: datetime | None,
) -> str:
    """Build the user-facing onboarding-task assignment message body."""
    base = f"{task_title} for {employee_full_name}."
    if due_at is None:
        return base
    normalized_due_at = _normalize_datetime(due_at)
    if normalized_due_at is None:
        return base
    return f"{base} Due at {normalized_due_at.isoformat()}."
