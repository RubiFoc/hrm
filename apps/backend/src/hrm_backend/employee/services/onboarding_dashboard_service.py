"""Business service for HR/manager onboarding progress dashboard reads."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.dao.onboarding_run_dao import OnboardingRunDAO
from hrm_backend.employee.dao.onboarding_task_dao import OnboardingTaskDAO
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.schemas.onboarding import (
    OnboardingDashboardDetailResponse,
    OnboardingDashboardListItemResponse,
    OnboardingDashboardListResponse,
    OnboardingDashboardSummaryResponse,
    OnboardingDashboardTaskResponse,
    OnboardingTaskStatus,
)
from hrm_backend.rbac import Role

ONBOARDING_RUN_NOT_FOUND = "onboarding_run_not_found"


@dataclass(frozen=True)
class _RunMetrics:
    """Derived task counters for one onboarding run."""

    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    overdue_tasks: int


class OnboardingDashboardService:
    """Expose onboarding progress reads for HR and manager dashboard workflows."""

    def __init__(
        self,
        *,
        profile_dao: EmployeeProfileDAO,
        run_dao: OnboardingRunDAO,
        task_dao: OnboardingTaskDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize onboarding dashboard dependencies.

        Args:
            profile_dao: DAO for employee profile summaries.
            run_dao: DAO for onboarding run reads.
            task_dao: DAO for onboarding task reads.
            audit_service: Audit service for dashboard success and failure traces.
        """
        self._profile_dao = profile_dao
        self._run_dao = run_dao
        self._task_dao = task_dao
        self._audit_service = audit_service

    def list_runs(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
        search: str | None,
        task_status: OnboardingTaskStatus | None,
        assigned_role: Role | None,
        assigned_staff_id: UUID | None,
        overdue_only: bool,
        limit: int,
        offset: int,
    ) -> OnboardingDashboardListResponse:
        """List onboarding runs visible to the current staff user.

        Args:
            auth_context: Authenticated staff context.
            request: Active HTTP request.
            search: Optional employee search across name, e-mail, and title.
            task_status: Optional filter requiring at least one task with the selected status.
            assigned_role: Optional filter requiring at least one task assigned to the role.
            assigned_staff_id: Optional filter requiring at least one task assigned to the staff id.
            overdue_only: When `True`, return only runs with at least one overdue incomplete task.
            limit: Maximum number of items to return.
            offset: Zero-based pagination offset.

        Returns:
            OnboardingDashboardListResponse: Paginated dashboard rows and aggregate counters.
        """
        actor_role = _resolve_actor_role(auth_context)
        actor_subject_id = str(auth_context.subject_id)
        search_term = _normalize_search(search)
        assigned_staff_id_raw = str(assigned_staff_id) if assigned_staff_id is not None else None

        rows = self._load_visible_rows(
            actor_role=actor_role,
            actor_subject_id=actor_subject_id,
        )

        filtered_rows = [
            row
            for row in rows
            if _matches_dashboard_filters(
                row=row,
                search_term=search_term,
                task_status=task_status,
                assigned_role=assigned_role,
                assigned_staff_id=assigned_staff_id_raw,
                overdue_only=overdue_only,
            )
        ]

        filtered_rows.sort(
            key=lambda row: (
                -row.metrics.overdue_tasks,
                -int(row.run.started_at.timestamp()),
                row.run.onboarding_id,
            )
        )

        summary = _build_dashboard_summary(filtered_rows)
        paginated_rows = filtered_rows[offset : offset + limit]
        items = [
            _to_dashboard_list_item(row.profile, row.run, row.tasks, row.metrics)
            for row in paginated_rows
        ]

        self._audit_success(
            action="onboarding_dashboard:list",
            auth_context=auth_context,
            request=request,
        )
        return OnboardingDashboardListResponse(
            items=items,
            total=len(filtered_rows),
            limit=limit,
            offset=offset,
            summary=summary,
        )

    def get_run(
        self,
        *,
        onboarding_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> OnboardingDashboardDetailResponse:
        """Load one onboarding run detail payload for dashboard read workflows.

        Args:
            onboarding_id: Onboarding run identifier.
            auth_context: Authenticated staff context.
            request: Active HTTP request.

        Returns:
            OnboardingDashboardDetailResponse: Employee summary, progress counters, and tasks.

        Raises:
            HTTPException: If the onboarding run does not exist or is not visible to the actor.
        """
        actor_role = _resolve_actor_role(auth_context)
        actor_subject_id = str(auth_context.subject_id)
        run = self._run_dao.get_by_id(str(onboarding_id))
        if run is None:
            self._audit_failure(
                action="onboarding_dashboard:read",
                auth_context=auth_context,
                request=request,
                resource_id=str(onboarding_id),
                reason=ONBOARDING_RUN_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ONBOARDING_RUN_NOT_FOUND,
            )

        profile = self._profile_dao.get_by_id(run.employee_id)
        tasks = self._task_dao.list_by_onboarding_id(run.onboarding_id)
        if profile is None or not _can_actor_view_run(
            actor_role=actor_role,
            actor_subject_id=actor_subject_id,
            tasks=tasks,
        ):
            self._audit_failure(
                action="onboarding_dashboard:read",
                auth_context=auth_context,
                request=request,
                resource_id=str(onboarding_id),
                reason=ONBOARDING_RUN_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ONBOARDING_RUN_NOT_FOUND,
            )

        metrics = _build_metrics(tasks)
        self._audit_success(
            action="onboarding_dashboard:read",
            auth_context=auth_context,
            request=request,
            resource_id=str(onboarding_id),
        )
        return OnboardingDashboardDetailResponse(
            onboarding_id=UUID(run.onboarding_id),
            employee_id=UUID(profile.employee_id),
            first_name=profile.first_name,
            last_name=profile.last_name,
            email=profile.email,
            current_title=profile.current_title,
            location=profile.location,
            start_date=profile.start_date,
            offer_terms_summary=profile.offer_terms_summary,
            onboarding_status=run.status,
            onboarding_started_at=run.started_at,
            total_tasks=metrics.total_tasks,
            pending_tasks=metrics.pending_tasks,
            in_progress_tasks=metrics.in_progress_tasks,
            completed_tasks=metrics.completed_tasks,
            overdue_tasks=metrics.overdue_tasks,
            progress_percent=_calculate_progress_percent(metrics),
            tasks=[_to_dashboard_task_response(task) for task in tasks],
        )

    def _load_visible_rows(
        self,
        *,
        actor_role: Role,
        actor_subject_id: str,
    ) -> list[_DashboardRow]:
        """Load and pre-aggregate onboarding dashboard rows for the current actor."""
        runs = self._run_dao.list_runs()
        if not runs:
            return []

        tasks_by_onboarding = _group_tasks_by_onboarding(
            self._task_dao.list_by_onboarding_ids([run.onboarding_id for run in runs])
        )
        profiles_by_id = {
            profile.employee_id: profile
            for profile in self._profile_dao.list_by_ids([run.employee_id for run in runs])
        }

        rows: list[_DashboardRow] = []
        for run in runs:
            profile = profiles_by_id.get(run.employee_id)
            if profile is None:
                continue

            tasks = tasks_by_onboarding.get(run.onboarding_id, [])
            if not _can_actor_view_run(
                actor_role=actor_role,
                actor_subject_id=actor_subject_id,
                tasks=tasks,
            ):
                continue

            rows.append(
                _DashboardRow(
                    profile=profile,
                    run=run,
                    tasks=tasks,
                    metrics=_build_metrics(tasks),
                )
            )
        return rows

    def _audit_success(
        self,
        *,
        action: str,
        auth_context: AuthContext,
        request: Request,
        resource_id: str | None = None,
    ) -> None:
        """Record one successful onboarding dashboard audit event."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type="onboarding_dashboard",
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
        """Record one failed onboarding dashboard audit event."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type="onboarding_dashboard",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=resource_id,
            reason=reason,
        )


@dataclass(frozen=True)
class _DashboardRow:
    """In-memory onboarding dashboard row used for filtering and aggregation."""

    profile: EmployeeProfile
    run: OnboardingRun
    tasks: list[OnboardingTask]
    metrics: _RunMetrics


def _resolve_actor_role(auth_context: AuthContext) -> Role:
    """Resolve actor role from authenticated context for local visibility rules."""
    role = auth_context.role
    if role not in {"admin", "hr", "manager"}:
        return "hr"
    return role


def _group_tasks_by_onboarding(tasks: list[OnboardingTask]) -> dict[str, list[OnboardingTask]]:
    """Group task rows by onboarding run identifier."""
    grouped: dict[str, list[OnboardingTask]] = defaultdict(list)
    for task in tasks:
        grouped[task.onboarding_id].append(task)
    return dict(grouped)


def _build_metrics(tasks: list[OnboardingTask]) -> _RunMetrics:
    """Derive task counters and overdue state for one onboarding run."""
    now = datetime.now(UTC)
    pending_tasks = 0
    in_progress_tasks = 0
    completed_tasks = 0
    overdue_tasks = 0

    for task in tasks:
        if task.status == "pending":
            pending_tasks += 1
        elif task.status == "in_progress":
            in_progress_tasks += 1
        elif task.status == "completed":
            completed_tasks += 1

        due_at = task.due_at
        if (
            due_at is not None
            and task.status != "completed"
            and _normalize_datetime(due_at) < now
        ):
            overdue_tasks += 1

    return _RunMetrics(
        total_tasks=len(tasks),
        pending_tasks=pending_tasks,
        in_progress_tasks=in_progress_tasks,
        completed_tasks=completed_tasks,
        overdue_tasks=overdue_tasks,
    )


def _normalize_datetime(value: datetime) -> datetime:
    """Normalize task timestamp into UTC-aware value for comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _can_actor_view_run(
    *,
    actor_role: Role,
    actor_subject_id: str,
    tasks: list[OnboardingTask],
) -> bool:
    """Apply dashboard visibility rules for HR/admin and manager actors."""
    if actor_role in {"admin", "hr"}:
        return True
    if actor_role != "manager":
        return False
    return any(
        task.assigned_role == "manager" or task.assigned_staff_id == actor_subject_id
        for task in tasks
    )


def _normalize_search(search: str | None) -> str | None:
    """Normalize search term for dashboard text matching."""
    candidate = search.strip().lower() if search else ""
    return candidate or None


def _matches_dashboard_filters(
    *,
    row: _DashboardRow,
    search_term: str | None,
    task_status: OnboardingTaskStatus | None,
    assigned_role: Role | None,
    assigned_staff_id: str | None,
    overdue_only: bool,
) -> bool:
    """Evaluate dashboard row against list filters."""
    if search_term is not None:
        haystack = " ".join(
            part
            for part in [
                row.profile.first_name,
                row.profile.last_name,
                row.profile.email,
                row.profile.current_title or "",
            ]
            if part
        ).lower()
        if search_term not in haystack:
            return False

    if task_status is not None and not any(task.status == task_status for task in row.tasks):
        return False

    if assigned_role is not None and not any(
        task.assigned_role == assigned_role for task in row.tasks
    ):
        return False

    if assigned_staff_id is not None and not any(
        task.assigned_staff_id == assigned_staff_id for task in row.tasks
    ):
        return False

    if overdue_only and row.metrics.overdue_tasks == 0:
        return False

    return True


def _build_dashboard_summary(rows: list[_DashboardRow]) -> OnboardingDashboardSummaryResponse:
    """Aggregate dashboard counters for the current filtered row set."""
    return OnboardingDashboardSummaryResponse(
        run_count=len(rows),
        total_tasks=sum(row.metrics.total_tasks for row in rows),
        pending_tasks=sum(row.metrics.pending_tasks for row in rows),
        in_progress_tasks=sum(row.metrics.in_progress_tasks for row in rows),
        completed_tasks=sum(row.metrics.completed_tasks for row in rows),
        overdue_tasks=sum(row.metrics.overdue_tasks for row in rows),
    )


def _to_dashboard_list_item(
    profile: EmployeeProfile,
    run: OnboardingRun,
    tasks: list[OnboardingTask],
    metrics: _RunMetrics,
) -> OnboardingDashboardListItemResponse:
    """Map one dashboard row to list response schema."""
    del tasks
    return OnboardingDashboardListItemResponse(
        onboarding_id=UUID(run.onboarding_id),
        employee_id=UUID(profile.employee_id),
        first_name=profile.first_name,
        last_name=profile.last_name,
        email=profile.email,
        current_title=profile.current_title,
        location=profile.location,
        start_date=profile.start_date,
        onboarding_status=run.status,
        onboarding_started_at=run.started_at,
        total_tasks=metrics.total_tasks,
        pending_tasks=metrics.pending_tasks,
        in_progress_tasks=metrics.in_progress_tasks,
        completed_tasks=metrics.completed_tasks,
        overdue_tasks=metrics.overdue_tasks,
        progress_percent=_calculate_progress_percent(metrics),
    )


def _to_dashboard_task_response(task: OnboardingTask) -> OnboardingDashboardTaskResponse:
    """Map onboarding task row to dashboard detail task schema."""
    return OnboardingDashboardTaskResponse(
        task_id=UUID(task.task_id),
        code=task.code,
        title=task.title,
        description=task.description,
        sort_order=task.sort_order,
        is_required=task.is_required,
        status=task.status,
        assigned_role=task.assigned_role,
        assigned_staff_id=UUID(task.assigned_staff_id) if task.assigned_staff_id else None,
        due_at=task.due_at,
        completed_at=task.completed_at,
        updated_at=task.updated_at,
    )


def _calculate_progress_percent(metrics: _RunMetrics) -> int:
    """Convert task counters into integer completion progress percentage."""
    if metrics.total_tasks == 0:
        return 0
    return round((metrics.completed_tasks / metrics.total_tasks) * 100)
