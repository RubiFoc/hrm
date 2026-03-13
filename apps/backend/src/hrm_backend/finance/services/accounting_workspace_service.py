"""Business service for accountant workspace reads and controlled exports."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Request

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.employee.dao.onboarding_task_dao import OnboardingTaskDAO
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.finance.dao import AccountingWorkspaceDAO
from hrm_backend.finance.schemas.workspace import (
    AccountingWorkspaceExportFormat,
    AccountingWorkspaceListResponse,
    AccountingWorkspaceRowResponse,
)
from hrm_backend.finance.utils.exports import (
    render_accounting_workspace_csv,
    render_accounting_workspace_xlsx,
)

ACCOUNTING_WORKSPACE_READ_ACTION = "accounting_workspace:read"
ACCOUNTING_WORKSPACE_EXPORT_ACTION = "accounting_export:download"


@dataclass(frozen=True)
class AccountingWorkspaceExportPayload:
    """Binary export payload returned by accountant workspace export service.

    Attributes:
        content: Attachment bytes.
        media_type: HTTP content type for the attachment.
        filename: Attachment filename returned in `Content-Disposition`.
    """

    content: bytes
    media_type: str
    filename: str


class AccountingWorkspaceService:
    """Serve accountant-visible onboarding rows and file exports.

    Inputs:
        - authenticated accountant or admin context from the current request;
        - onboarding runs joined with employee profiles;
        - onboarding tasks used as the only visibility signal for accountant scope.

    Outputs:
        - paginated accountant workspace rows for UI rendering;
        - CSV or XLSX attachments containing the same filtered row set.

    Side effects:
        - records audit events for workspace reads and export downloads.
    """

    def __init__(
        self,
        *,
        workspace_dao: AccountingWorkspaceDAO,
        task_dao: OnboardingTaskDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize accountant workspace service dependencies."""
        self._workspace_dao = workspace_dao
        self._task_dao = task_dao
        self._audit_service = audit_service

    def list_workspace(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
        search: str | None,
        limit: int,
        offset: int,
    ) -> AccountingWorkspaceListResponse:
        """Return the paginated accountant workspace rows visible to the current actor."""
        rows = self._load_visible_rows(
            actor_subject_id=str(auth_context.subject_id),
            search=search,
        )
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=ACCOUNTING_WORKSPACE_READ_ACTION,
            resource_type="accounting_workspace",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
        )
        return AccountingWorkspaceListResponse(
            items=rows[offset : offset + limit],
            total=len(rows),
            limit=limit,
            offset=offset,
        )

    def export_workspace(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
        search: str | None,
        export_format: AccountingWorkspaceExportFormat,
    ) -> AccountingWorkspaceExportPayload:
        """Render the full filtered accountant workspace scope as a downloadable attachment."""
        rows = self._load_visible_rows(
            actor_subject_id=str(auth_context.subject_id),
            search=search,
        )
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=ACCOUNTING_WORKSPACE_EXPORT_ACTION,
            resource_type="accounting_workspace_export",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            reason=export_format,
        )
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        if export_format == "csv":
            return AccountingWorkspaceExportPayload(
                content=render_accounting_workspace_csv(rows),
                media_type="text/csv",
                filename=f"accounting-workspace-{timestamp}.csv",
            )
        return AccountingWorkspaceExportPayload(
            content=render_accounting_workspace_xlsx(rows),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"accounting-workspace-{timestamp}.xlsx",
        )

    def _load_visible_rows(
        self,
        *,
        actor_subject_id: str,
        search: str | None,
    ) -> list[AccountingWorkspaceRowResponse]:
        """Load accountant-visible workspace rows for one actor and optional search term."""
        pairs = self._workspace_dao.list_runs_with_profiles()
        onboarding_ids = [run.onboarding_id for run, _profile in pairs]
        tasks_by_onboarding: dict[str, list[OnboardingTask]] = defaultdict(list)
        for task in self._task_dao.list_by_onboarding_ids(onboarding_ids):
            tasks_by_onboarding[task.onboarding_id].append(task)

        search_term = _normalize_search(search)
        rows: list[AccountingWorkspaceRowResponse] = []
        for run, profile in pairs:
            accountant_tasks = _select_actor_accounting_tasks(
                tasks=tasks_by_onboarding.get(run.onboarding_id, []),
                actor_subject_id=actor_subject_id,
            )
            if not accountant_tasks:
                continue
            row = _to_accounting_workspace_row(
                profile=profile,
                onboarding_run=run,
                accountant_tasks=accountant_tasks,
            )
            if search_term is not None and not _matches_search(row=row, search_term=search_term):
                continue
            rows.append(row)
        return rows


def _select_actor_accounting_tasks(
    *,
    tasks: list[OnboardingTask],
    actor_subject_id: str,
) -> list[OnboardingTask]:
    """Filter onboarding tasks down to the accountant-visible scope for one actor."""
    return [
        task
        for task in tasks
        if task.assigned_role == "accountant" or task.assigned_staff_id == actor_subject_id
    ]


def _to_accounting_workspace_row(
    *,
    profile: EmployeeProfile,
    onboarding_run: OnboardingRun,
    accountant_tasks: list[OnboardingTask],
) -> AccountingWorkspaceRowResponse:
    """Map one employee/onboarding bundle into the accountant workspace row shape."""
    pending = 0
    in_progress = 0
    completed = 0
    overdue = 0
    latest_due_at: datetime | None = None
    now = datetime.now(UTC)
    for task in accountant_tasks:
        if task.status == "pending":
            pending += 1
        elif task.status == "in_progress":
            in_progress += 1
        elif task.status == "completed":
            completed += 1

        if task.due_at is not None:
            normalized_due_at = _normalize_datetime(task.due_at)
            if latest_due_at is None or normalized_due_at > latest_due_at:
                latest_due_at = normalized_due_at
            if task.status != "completed" and normalized_due_at < now:
                overdue += 1

    return AccountingWorkspaceRowResponse(
        onboarding_id=UUID(onboarding_run.onboarding_id),
        employee_id=UUID(profile.employee_id),
        first_name=profile.first_name,
        last_name=profile.last_name,
        email=profile.email,
        location=profile.location,
        current_title=profile.current_title,
        start_date=profile.start_date,
        offer_terms_summary=profile.offer_terms_summary,
        onboarding_status=onboarding_run.status,
        accountant_task_total=len(accountant_tasks),
        accountant_task_pending=pending,
        accountant_task_in_progress=in_progress,
        accountant_task_completed=completed,
        accountant_task_overdue=overdue,
        latest_accountant_due_at=latest_due_at,
    )


def _normalize_search(search: str | None) -> str | None:
    """Normalize optional search input into lowercase token or `None`."""
    candidate = search.strip().lower() if search else ""
    return candidate or None


def _matches_search(
    *,
    row: AccountingWorkspaceRowResponse,
    search_term: str,
) -> bool:
    """Evaluate accountant workspace row against the normalized search term."""
    haystack = " ".join(
        part
        for part in [
            row.first_name,
            row.last_name,
            row.email,
            row.location or "",
            row.current_title or "",
            row.offer_terms_summary or "",
        ]
        if part
    ).lower()
    return search_term in haystack


def _normalize_datetime(value: datetime) -> datetime:
    """Normalize timestamps into UTC-aware values for comparisons and export consistency."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
