"""Request, response, and internal payloads for onboarding workflow artifacts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from hrm_backend.employee.utils.onboarding import (
    ONBOARDING_RUN_STATUS_STARTED,
    ONBOARDING_TASK_STATUS_PENDING,
)
from hrm_backend.rbac import Role

OnboardingRunStatus = Literal["started"]
OnboardingTaskStatus = Literal["pending", "in_progress", "completed"]


class OnboardingRunCreate(BaseModel):
    """Internal service payload for one persisted onboarding-start artifact.

    Attributes:
        employee_id: Employee profile identifier that owns the onboarding run.
        hire_conversion_id: Source hire-conversion identifier copied from the employee profile.
        status: Minimal onboarding lifecycle state for the initial trigger slice.
        started_by_staff_id: Staff subject that triggered employee bootstrap.
    """

    model_config = ConfigDict(extra="forbid")

    employee_id: UUID
    hire_conversion_id: UUID
    status: OnboardingRunStatus = ONBOARDING_RUN_STATUS_STARTED
    started_by_staff_id: UUID


class OnboardingTaskCreate(BaseModel):
    """Internal service payload for one generated onboarding task."""

    model_config = ConfigDict(extra="forbid")

    onboarding_id: UUID
    template_id: UUID
    template_item_id: UUID
    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    description: str | None = None
    sort_order: int = Field(ge=0)
    is_required: bool = True
    status: OnboardingTaskStatus = ONBOARDING_TASK_STATUS_PENDING
    assigned_role: Role | None = None
    assigned_staff_id: UUID | None = None
    due_at: datetime | None = None


class OnboardingTaskUpdateRequest(BaseModel):
    """Staff-facing partial update payload for one onboarding task."""

    model_config = ConfigDict(extra="forbid")

    status: OnboardingTaskStatus | None = None
    assigned_role: Role | None = None
    assigned_staff_id: UUID | None = None
    due_at: datetime | None = None

    @model_validator(mode="after")
    def validate_non_nullable_status(self) -> OnboardingTaskUpdateRequest:
        """Reject explicit `null` for status while allowing omitted field updates."""
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("status cannot be null")
        return self


class OnboardingTaskResponse(BaseModel):
    """API representation of one onboarding task."""

    task_id: UUID
    onboarding_id: UUID
    template_id: UUID
    template_item_id: UUID
    code: str
    title: str
    description: str | None
    sort_order: int
    is_required: bool
    status: OnboardingTaskStatus
    assigned_role: Role | None
    assigned_staff_id: UUID | None
    due_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OnboardingTaskListResponse(BaseModel):
    """List payload for onboarding tasks belonging to one onboarding run."""

    items: list[OnboardingTaskResponse]


class OnboardingDashboardSummaryResponse(BaseModel):
    """Aggregated onboarding progress counters for the current filtered dashboard scope."""

    run_count: int
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    overdue_tasks: int


class OnboardingDashboardListItemResponse(BaseModel):
    """Dashboard summary row for one onboarding run plus employee context."""

    onboarding_id: UUID
    employee_id: UUID
    first_name: str
    last_name: str
    email: str
    current_title: str | None
    location: str | None
    start_date: date | None
    onboarding_status: OnboardingRunStatus
    onboarding_started_at: datetime
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    overdue_tasks: int
    progress_percent: int = Field(ge=0, le=100)


class OnboardingDashboardListResponse(BaseModel):
    """Paginated onboarding dashboard payload for staff progress tracking."""

    items: list[OnboardingDashboardListItemResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    summary: OnboardingDashboardSummaryResponse


class OnboardingDashboardTaskResponse(BaseModel):
    """Read-only onboarding task representation used inside dashboard detail views."""

    task_id: UUID
    code: str
    title: str
    description: str | None
    sort_order: int
    is_required: bool
    status: OnboardingTaskStatus
    assigned_role: Role | None
    assigned_staff_id: UUID | None
    due_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime


class OnboardingDashboardDetailResponse(BaseModel):
    """Detailed onboarding dashboard payload for one onboarding run."""

    onboarding_id: UUID
    employee_id: UUID
    first_name: str
    last_name: str
    email: str
    current_title: str | None
    location: str | None
    start_date: date | None
    offer_terms_summary: str | None
    onboarding_status: OnboardingRunStatus
    onboarding_started_at: datetime
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    overdue_tasks: int
    progress_percent: int = Field(ge=0, le=100)
    tasks: list[OnboardingDashboardTaskResponse]


class EmployeeOnboardingTaskUpdateRequest(BaseModel):
    """Employee-facing request payload for updating one actionable onboarding task.

    Attributes:
        status: Next employee-managed task status.
    """

    model_config = ConfigDict(extra="forbid")

    status: OnboardingTaskStatus


class EmployeeOnboardingTaskResponse(BaseModel):
    """Employee-facing API representation of one onboarding checklist task."""

    task_id: UUID
    onboarding_id: UUID
    code: str
    title: str
    description: str | None
    sort_order: int
    is_required: bool
    status: OnboardingTaskStatus
    assigned_role: Role | None
    assigned_staff_id: UUID | None
    due_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    can_update: bool


class EmployeeOnboardingPortalResponse(BaseModel):
    """Employee-facing onboarding portal payload scoped to the current user."""

    employee_id: UUID
    first_name: str
    last_name: str
    email: str
    location: str | None
    current_title: str | None
    start_date: date | None
    offer_terms_summary: str | None
    onboarding_id: UUID | None
    onboarding_status: OnboardingRunStatus | None
    onboarding_started_at: datetime | None
    tasks: list[EmployeeOnboardingTaskResponse]
