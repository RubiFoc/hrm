"""Business service for employee self-service onboarding portal reads and updates."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.dao.onboarding_run_dao import OnboardingRunDAO
from hrm_backend.employee.dao.onboarding_task_dao import OnboardingTaskDAO
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.schemas.onboarding import (
    EmployeeOnboardingPortalResponse,
    EmployeeOnboardingTaskResponse,
    EmployeeOnboardingTaskUpdateRequest,
)
from hrm_backend.employee.utils.onboarding import ONBOARDING_TASK_STATUS_COMPLETED

EMPLOYEE_PROFILE_NOT_FOUND = "employee_profile_not_found"
EMPLOYEE_PROFILE_IDENTITY_CONFLICT = "employee_profile_identity_conflict"
EMPLOYEE_ONBOARDING_NOT_FOUND = "employee_onboarding_not_found"
ONBOARDING_TASK_NOT_FOUND = "onboarding_task_not_found"
ONBOARDING_TASK_NOT_ACTIONABLE_BY_EMPLOYEE = "onboarding_task_not_actionable_by_employee"


class EmployeeOnboardingPortalService:
    """Expose onboarding tasks for the authenticated employee and allow self-updates."""

    def __init__(
        self,
        *,
        profile_dao: EmployeeProfileDAO,
        run_dao: OnboardingRunDAO,
        task_dao: OnboardingTaskDAO,
        staff_account_dao: StaffAccountDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize employee self-service onboarding dependencies.

        Args:
            profile_dao: DAO for employee profile lookup and identity-link writes.
            run_dao: DAO for onboarding-run lookup by employee profile.
            task_dao: DAO for onboarding task reads and writes.
            staff_account_dao: DAO for authenticated staff-account lookups.
            audit_service: Audit service for portal success and failure traces.
        """
        self._profile_dao = profile_dao
        self._run_dao = run_dao
        self._task_dao = task_dao
        self._staff_account_dao = staff_account_dao
        self._audit_service = audit_service

    def get_portal(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeOnboardingPortalResponse:
        """Load self-service onboarding portal payload for the authenticated employee.

        Args:
            auth_context: Authenticated employee context.
            request: Active HTTP request.

        Returns:
            EmployeeOnboardingPortalResponse: Employee-scoped onboarding summary and tasks.

        Raises:
            HTTPException: If the employee profile cannot be resolved from the authenticated
                subject or identity linkage conflicts with existing data.
        """
        try:
            profile = self._resolve_profile(auth_context=auth_context)
        except HTTPException as exc:
            self._audit_portal_failure(
                action="employee_portal:read",
                auth_context=auth_context,
                request=request,
                reason=str(exc.detail),
            )
            raise

        onboarding = self._run_dao.get_by_employee_id(profile.employee_id)
        tasks = (
            self._task_dao.list_by_onboarding_id(onboarding.onboarding_id)
            if onboarding is not None
            else []
        )
        self._audit_portal_success(
            action="employee_portal:read",
            auth_context=auth_context,
            request=request,
            resource_id=profile.employee_id,
        )
        return _to_portal_response(
            profile=profile,
            onboarding=onboarding,
            tasks=tasks,
            actor_subject_id=str(auth_context.subject_id),
        )

    def update_task(
        self,
        *,
        task_id: UUID,
        payload: EmployeeOnboardingTaskUpdateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeOnboardingTaskResponse:
        """Update one employee-actionable onboarding task for the authenticated employee.

        Args:
            task_id: Task identifier scoped to the current employee onboarding run.
            payload: Employee-facing task status update.
            auth_context: Authenticated employee context.
            request: Active HTTP request.

        Returns:
            EmployeeOnboardingTaskResponse: Updated task payload with current self-actionability.

        Raises:
            HTTPException: If the employee profile or onboarding run is missing, the task is
                missing, or the task is currently not actionable by the authenticated employee.
        """
        try:
            profile = self._resolve_profile(auth_context=auth_context)
        except HTTPException as exc:
            self._audit_task_failure(
                action="employee_portal:update",
                auth_context=auth_context,
                request=request,
                reason=str(exc.detail),
            )
            raise

        onboarding = self._run_dao.get_by_employee_id(profile.employee_id)
        if onboarding is None:
            self._audit_task_failure(
                action="employee_portal:update",
                auth_context=auth_context,
                request=request,
                resource_id=str(task_id),
                reason=EMPLOYEE_ONBOARDING_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_ONBOARDING_NOT_FOUND,
            )

        task = self._task_dao.get_by_onboarding_and_id(
            onboarding_id=onboarding.onboarding_id,
            task_id=str(task_id),
        )
        if task is None:
            self._audit_task_failure(
                action="employee_portal:update",
                auth_context=auth_context,
                request=request,
                resource_id=str(task_id),
                reason=ONBOARDING_TASK_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ONBOARDING_TASK_NOT_FOUND,
            )

        actor_subject_id = str(auth_context.subject_id)
        if not _can_employee_update_task(task=task, actor_subject_id=actor_subject_id):
            self._audit_task_failure(
                action="employee_portal:update",
                auth_context=auth_context,
                request=request,
                resource_id=task.task_id,
                reason=ONBOARDING_TASK_NOT_ACTIONABLE_BY_EMPLOYEE,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ONBOARDING_TASK_NOT_ACTIONABLE_BY_EMPLOYEE,
            )

        task.status = payload.status
        if payload.status == ONBOARDING_TASK_STATUS_COMPLETED:
            task.completed_at = datetime.now(UTC)
        else:
            task.completed_at = None

        updated = self._task_dao.update_task(entity=task)
        self._audit_task_success(
            action="employee_portal:update",
            auth_context=auth_context,
            request=request,
            resource_id=updated.task_id,
        )
        return _to_employee_task_response(
            entity=updated,
            actor_subject_id=actor_subject_id,
        )

    def _resolve_profile(self, *, auth_context: AuthContext) -> EmployeeProfile:
        """Resolve employee profile for the authenticated employee subject.

        The method first checks for a durable `employee_profiles.staff_account_id` link. When the
        link does not exist yet, it falls back to exact e-mail reconciliation against the current
        authenticated staff account and persists the link for later requests.

        Args:
            auth_context: Authenticated employee context.

        Returns:
            EmployeeProfile: Resolved and, if needed, newly-linked employee profile.

        Raises:
            HTTPException: If no unique employee profile can be resolved from the current identity.
        """
        subject_id = str(auth_context.subject_id)
        linked = self._profile_dao.get_by_staff_account_id(subject_id)
        if linked is not None:
            return linked

        account = self._staff_account_dao.get_by_id(subject_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_PROFILE_NOT_FOUND,
            )

        matches = self._profile_dao.list_by_email(account.email)
        if not matches:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_PROFILE_NOT_FOUND,
            )
        if len(matches) > 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=EMPLOYEE_PROFILE_IDENTITY_CONFLICT,
            )

        profile = matches[0]
        if profile.staff_account_id is not None and profile.staff_account_id != subject_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=EMPLOYEE_PROFILE_IDENTITY_CONFLICT,
            )

        profile.staff_account_id = subject_id
        return self._profile_dao.update_profile(entity=profile)

    def _audit_portal_success(
        self,
        *,
        action: str,
        auth_context: AuthContext,
        request: Request,
        resource_id: str,
    ) -> None:
        """Record one successful employee-portal audit event."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type="employee_portal",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=resource_id,
        )

    def _audit_portal_failure(
        self,
        *,
        action: str,
        auth_context: AuthContext,
        request: Request,
        reason: str,
    ) -> None:
        """Record one failed employee-portal audit event."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type="employee_portal",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            reason=reason,
        )

    def _audit_task_success(
        self,
        *,
        action: str,
        auth_context: AuthContext,
        request: Request,
        resource_id: str,
    ) -> None:
        """Record one successful employee task-update audit event."""
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

    def _audit_task_failure(
        self,
        *,
        action: str,
        auth_context: AuthContext,
        request: Request,
        reason: str,
        resource_id: str | None = None,
    ) -> None:
        """Record one failed employee task-update audit event."""
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


def _can_employee_update_task(*, task: OnboardingTask, actor_subject_id: str) -> bool:
    """Decide whether one onboarding task is actionable by the authenticated employee.

    Args:
        task: Onboarding task entity scoped to the current employee.
        actor_subject_id: Authenticated staff-account subject identifier for the employee.

    Returns:
        bool: `True` when the task is unassigned or explicitly assigned to the employee role and,
        when a concrete subject assignment exists, that assignment targets the current employee.
    """
    role_allows = task.assigned_role in (None, "employee")
    subject_allows = task.assigned_staff_id in (None, actor_subject_id)
    return role_allows and subject_allows


def _to_portal_response(
    *,
    profile: EmployeeProfile,
    onboarding: OnboardingRun | None,
    tasks: list[OnboardingTask],
    actor_subject_id: str,
) -> EmployeeOnboardingPortalResponse:
    """Map employee profile, onboarding run, and tasks to self-service portal payload."""
    return EmployeeOnboardingPortalResponse(
        employee_id=profile.employee_id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        email=profile.email,
        location=profile.location,
        current_title=profile.current_title,
        start_date=profile.start_date,
        offer_terms_summary=profile.offer_terms_summary,
        onboarding_id=onboarding.onboarding_id if onboarding is not None else None,
        onboarding_status=onboarding.status if onboarding is not None else None,
        onboarding_started_at=onboarding.started_at if onboarding is not None else None,
        tasks=[
            _to_employee_task_response(entity=task, actor_subject_id=actor_subject_id)
            for task in tasks
        ],
    )


def _to_employee_task_response(
    *,
    entity: OnboardingTask,
    actor_subject_id: str,
) -> EmployeeOnboardingTaskResponse:
    """Map onboarding task entity to employee-facing task payload."""
    return EmployeeOnboardingTaskResponse(
        task_id=entity.task_id,
        onboarding_id=entity.onboarding_id,
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
        can_update=_can_employee_update_task(
            task=entity,
            actor_subject_id=actor_subject_id,
        ),
    )
