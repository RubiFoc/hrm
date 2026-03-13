"""Request and response schemas for accountant workspace APIs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from hrm_backend.employee.schemas.onboarding import OnboardingRunStatus

AccountingWorkspaceExportFormat = Literal["csv", "xlsx"]


class AccountingWorkspaceRowResponse(BaseModel):
    """One flattened accountant-visible onboarding row shared by UI and export generation."""

    onboarding_id: UUID
    employee_id: UUID
    first_name: str
    last_name: str
    email: str
    location: str | None
    current_title: str | None
    start_date: date | None
    offer_terms_summary: str | None
    onboarding_status: OnboardingRunStatus
    accountant_task_total: int = Field(ge=0)
    accountant_task_pending: int = Field(ge=0)
    accountant_task_in_progress: int = Field(ge=0)
    accountant_task_completed: int = Field(ge=0)
    accountant_task_overdue: int = Field(ge=0)
    latest_accountant_due_at: datetime | None = None


class AccountingWorkspaceListResponse(BaseModel):
    """Paginated accountant workspace payload for the current actor."""

    items: list[AccountingWorkspaceRowResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
