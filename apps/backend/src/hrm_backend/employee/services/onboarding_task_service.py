"""Business service for materialized onboarding task generation and staff operations."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.dao.onboarding_run_dao import OnboardingRunDAO
from hrm_backend.employee.dao.onboarding_task_dao import OnboardingTaskDAO
from hrm_backend.employee.dao.onboarding_template_dao import OnboardingTemplateDAO
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.models.template import OnboardingTemplate, OnboardingTemplateItem
from hrm_backend.employee.schemas.onboarding import (
    OnboardingTaskCreate,
    OnboardingTaskListResponse,
    OnboardingTaskResponse,
    OnboardingTaskUpdateRequest,
)
from hrm_backend.employee.utils.onboarding import ONBOARDING_TASK_STATUS_COMPLETED
from hrm_backend.notifications.services.notification_service import NotificationService

ONBOARDING_RUN_NOT_FOUND = "onboarding_run_not_found"
ONBOARDING_TASK_NOT_FOUND = "onboarding_task_not_found"
ONBOARDING_TASKS_ALREADY_EXIST = "onboarding_tasks_already_exist"
ONBOARDING_TEMPLATE_NOT_CONFIGURED = "onboarding_template_not_configured"


class OnboardingTemplateNotConfiguredError(RuntimeError):
    """Raised when task generation is requested without one active onboarding template."""


class OnboardingTaskService:
    """Materialize onboarding tasks from the active template and expose staff operations."""

    def __init__(
        self,
        *,
        session: Session,
        run_dao: OnboardingRunDAO,
        task_dao: OnboardingTaskDAO,
        template_dao: OnboardingTemplateDAO,
        profile_dao: EmployeeProfileDAO,
        notification_service: NotificationService,
        audit_service: AuditService,
    ) -> None:
        """Initialize onboarding task service dependencies.

        Args:
            session: SQLAlchemy session used to bundle task writes atomically.
            run_dao: DAO for onboarding run lookups.
            task_dao: DAO for onboarding task rows.
            template_dao: DAO for active onboarding template resolution.
            profile_dao: DAO for employee profile lookups used in notification copy.
            notification_service: In-app notification service for assignment changes.
            audit_service: Audit service for success and failure traces.
        """
        self._session = session
        self._run_dao = run_dao
        self._task_dao = task_dao
        self._template_dao = template_dao
        self._profile_dao = profile_dao
        self._notification_service = notification_service
        self._audit_service = audit_service

    def build_create_payloads(
        self,
        *,
        onboarding_run: OnboardingRun,
        template: OnboardingTemplate,
        template_items: list[OnboardingTemplateItem],
    ) -> list[OnboardingTaskCreate]:
        """Build deterministic task payloads from one onboarding run and template bundle."""
        return [
            OnboardingTaskCreate(
                onboarding_id=UUID(onboarding_run.onboarding_id),
                template_id=UUID(template.template_id),
                template_item_id=UUID(item.template_item_id),
                code=item.code,
                title=item.title,
                description=item.description,
                sort_order=item.sort_order,
                is_required=item.is_required,
            )
            for item in sorted(
                template_items,
                key=lambda candidate: (candidate.sort_order, candidate.code),
            )
        ]

    def create_tasks_from_active_template(
        self,
        *,
        onboarding_run: OnboardingRun,
        commit: bool = True,
    ) -> list[OnboardingTask]:
        """Materialize onboarding tasks for one run from the current active template."""
        template = self._template_dao.get_active_template()
        if template is None:
            raise OnboardingTemplateNotConfiguredError(ONBOARDING_TEMPLATE_NOT_CONFIGURED)

        items = self._template_dao.list_items_for_template_ids([template.template_id])
        payloads = self.build_create_payloads(
            onboarding_run=onboarding_run,
            template=template,
            template_items=items,
        )
        return self._task_dao.create_tasks(payloads=payloads, commit=commit)

    def list_tasks(
        self,
        *,
        onboarding_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> OnboardingTaskListResponse:
        """List ordered onboarding tasks for one onboarding run."""
        run = self._run_dao.get_by_id(str(onboarding_id))
        if run is None:
            self._audit_failure(
                action="onboarding_task:list",
                auth_context=auth_context,
                request=request,
                resource_id=str(onboarding_id),
                reason=ONBOARDING_RUN_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ONBOARDING_RUN_NOT_FOUND,
            )

        tasks = self._task_dao.list_by_onboarding_id(run.onboarding_id)
        self._audit_success(
            action="onboarding_task:list",
            auth_context=auth_context,
            request=request,
            resource_id=run.onboarding_id,
        )
        return OnboardingTaskListResponse(items=[_to_task_response(task) for task in tasks])

    def update_task(
        self,
        *,
        onboarding_id: UUID,
        task_id: UUID,
        payload: OnboardingTaskUpdateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> OnboardingTaskResponse:
        """Apply staff-managed assignment/status/SLA updates to one onboarding task."""
        run = self._run_dao.get_by_id(str(onboarding_id))
        if run is None:
            self._audit_failure(
                action="onboarding_task:update",
                auth_context=auth_context,
                request=request,
                resource_id=str(onboarding_id),
                reason=ONBOARDING_RUN_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ONBOARDING_RUN_NOT_FOUND,
            )

        entity = self._task_dao.get_by_onboarding_and_id(
            onboarding_id=run.onboarding_id,
            task_id=str(task_id),
        )
        if entity is None:
            self._audit_failure(
                action="onboarding_task:update",
                auth_context=auth_context,
                request=request,
                resource_id=str(task_id),
                reason=ONBOARDING_TASK_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ONBOARDING_TASK_NOT_FOUND,
            )

        previous_assigned_role = entity.assigned_role
        previous_assigned_staff_id = entity.assigned_staff_id
        if "status" in payload.model_fields_set:
            entity.status = payload.status or entity.status
            if payload.status == ONBOARDING_TASK_STATUS_COMPLETED:
                entity.completed_at = datetime.now(UTC)
            elif payload.status is not None:
                entity.completed_at = None
        if "assigned_role" in payload.model_fields_set:
            entity.assigned_role = payload.assigned_role
        if "assigned_staff_id" in payload.model_fields_set:
            entity.assigned_staff_id = (
                str(payload.assigned_staff_id) if payload.assigned_staff_id is not None else None
            )
        if "due_at" in payload.model_fields_set:
            entity.due_at = payload.due_at

        updated = self._task_dao.update_task(entity=entity, commit=False)
        profile = self._profile_dao.get_by_id(run.employee_id)
        self._notification_service.emit_onboarding_task_assignment_notifications(
            task=updated,
            employee_id=run.employee_id,
            employee_full_name=_resolve_employee_full_name(profile),
            previous_assigned_role=previous_assigned_role,
            previous_assigned_staff_id=previous_assigned_staff_id,
        )
        self._session.commit()
        self._session.refresh(updated)
        self._audit_success(
            action="onboarding_task:update",
            auth_context=auth_context,
            request=request,
            resource_id=updated.task_id,
        )
        return _to_task_response(updated)

    def backfill_tasks(
        self,
        *,
        onboarding_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> OnboardingTaskListResponse:
        """Generate onboarding tasks for one legacy onboarding run that has none yet."""
        run = self._run_dao.get_by_id(str(onboarding_id))
        if run is None:
            self._audit_failure(
                action="onboarding_task:backfill",
                auth_context=auth_context,
                request=request,
                resource_id=str(onboarding_id),
                reason=ONBOARDING_RUN_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ONBOARDING_RUN_NOT_FOUND,
            )

        existing_tasks = self._task_dao.list_by_onboarding_id(run.onboarding_id)
        if existing_tasks:
            self._audit_failure(
                action="onboarding_task:backfill",
                auth_context=auth_context,
                request=request,
                resource_id=run.onboarding_id,
                reason=ONBOARDING_TASKS_ALREADY_EXIST,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ONBOARDING_TASKS_ALREADY_EXIST,
            )

        try:
            tasks = self.create_tasks_from_active_template(onboarding_run=run)
        except OnboardingTemplateNotConfiguredError as exc:
            self._audit_failure(
                action="onboarding_task:backfill",
                auth_context=auth_context,
                request=request,
                resource_id=run.onboarding_id,
                reason=ONBOARDING_TEMPLATE_NOT_CONFIGURED,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=ONBOARDING_TEMPLATE_NOT_CONFIGURED,
            ) from exc

        self._audit_success(
            action="onboarding_task:backfill",
            auth_context=auth_context,
            request=request,
            resource_id=run.onboarding_id,
        )
        return OnboardingTaskListResponse(items=[_to_task_response(task) for task in tasks])

    def _audit_success(
        self,
        *,
        action: str,
        auth_context: AuthContext,
        request: Request,
        resource_id: str | None = None,
    ) -> None:
        """Record one successful onboarding-task audit event."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type="onboarding_task",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=resource_id,
        )

    def _audit_failure(
        self,
        *,
        action: str,
        auth_context: AuthContext,
        request: Request,
        reason: str,
        resource_id: str | None = None,
    ) -> None:
        """Record one failed onboarding-task audit event."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type="onboarding_task",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=resource_id,
            reason=reason,
        )


def _to_task_response(entity: OnboardingTask) -> OnboardingTaskResponse:
    """Map onboarding task entity to API response schema."""
    return OnboardingTaskResponse(
        task_id=entity.task_id,
        onboarding_id=entity.onboarding_id,
        template_id=entity.template_id,
        template_item_id=entity.template_item_id,
        code=entity.code,
        title=entity.title,
        description=entity.description,
        sort_order=entity.sort_order,
        is_required=entity.is_required,
        status=entity.status,
        assigned_role=entity.assigned_role,
        assigned_staff_id=entity.assigned_staff_id,
        due_at=entity.due_at,
        completed_at=entity.completed_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _resolve_employee_full_name(profile: EmployeeProfile | None) -> str:
    """Resolve a human-readable employee label for notification copy."""
    if profile is None:
        return "employee"
    full_name = f"{profile.first_name} {profile.last_name}".strip()
    return full_name or "employee"
