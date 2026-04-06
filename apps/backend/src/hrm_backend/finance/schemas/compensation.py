"""Schemas for compensation controls and read models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

CompensationRaiseStatus = Literal[
    "pending_confirmations",
    "awaiting_leader",
    "approved",
    "rejected",
]
BandAlignmentStatus = Literal["below_band", "within_band", "above_band"]


class CompensationRaiseCreateRequest(BaseModel):
    """Input payload for manager-initiated raise request creation."""

    model_config = ConfigDict(extra="forbid")

    employee_id: UUID
    proposed_base_salary: float = Field(gt=0)
    effective_date: date


class CompensationRaiseDecisionRequest(BaseModel):
    """Input payload for leader approval or rejection decisions."""

    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=2048)


class CompensationRaiseResponse(BaseModel):
    """Response payload for raise request state."""

    request_id: UUID
    employee_id: UUID
    requested_by_staff_id: UUID
    requested_at: datetime
    effective_date: date
    proposed_base_salary: float
    currency: str
    status: CompensationRaiseStatus
    confirmation_count: int
    confirmation_quorum: int
    leader_decision_by_staff_id: UUID | None
    leader_decision_at: datetime | None
    leader_decision_note: str | None


class CompensationRaiseListResponse(BaseModel):
    """Paginated raise request list response."""

    items: list[CompensationRaiseResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class SalaryBandCreateRequest(BaseModel):
    """Input payload for HR salary-band creation."""

    model_config = ConfigDict(extra="forbid")

    vacancy_id: UUID
    min_amount: float = Field(gt=0)
    max_amount: float = Field(gt=0)


class SalaryBandResponse(BaseModel):
    """Salary-band history item response."""

    band_id: UUID
    vacancy_id: UUID
    band_version: int
    min_amount: float
    max_amount: float
    currency: str
    created_by_staff_id: UUID
    created_at: datetime


class SalaryBandListResponse(BaseModel):
    """Salary-band list payload."""

    items: list[SalaryBandResponse]


class BonusUpsertRequest(BaseModel):
    """Input payload for manual bonus upsert."""

    model_config = ConfigDict(extra="forbid")

    employee_id: UUID
    period_month: date
    amount: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=2048)


class BonusEntryResponse(BaseModel):
    """Response payload for manual bonus entries."""

    bonus_id: UUID
    employee_id: UUID
    period_month: date
    amount: float
    currency: str
    note: str | None
    created_by_staff_id: UUID
    updated_by_staff_id: UUID | None
    created_at: datetime
    updated_at: datetime


class CompensationTableRowResponse(BaseModel):
    """Unified compensation table row returned to manager/HR/accountant roles."""

    employee_id: UUID
    full_name: str
    department: str | None
    position_title: str | None
    currency: str
    base_salary: float | None
    bonus_amount: float | None
    bonus_period_month: date | None
    salary_band_min: float | None
    salary_band_max: float | None
    band_alignment_status: BandAlignmentStatus | None
    last_raise_effective_date: date | None
    last_raise_status: CompensationRaiseStatus | None


class CompensationTableListResponse(BaseModel):
    """Paginated compensation table response."""

    items: list[CompensationTableRowResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
