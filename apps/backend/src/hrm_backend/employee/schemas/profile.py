"""Employee-profile request, response, and internal bootstrap schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from hrm_backend.employee.schemas.onboarding import OnboardingRunStatus


class EmployeeProfileCreateRequest(BaseModel):
    """Staff-facing request payload for employee profile creation.

    Attributes:
        vacancy_id: Vacancy identifier used to resolve the hire conversion.
        candidate_id: Candidate identifier used to resolve the hire conversion.
    """

    model_config = ConfigDict(extra="forbid")

    vacancy_id: UUID
    candidate_id: UUID


class EmployeeProfileCreate(BaseModel):
    """Internal typed payload for inserting one employee profile row."""

    model_config = ConfigDict(extra="forbid")

    hire_conversion_id: UUID
    vacancy_id: UUID
    candidate_id: UUID
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    email: str = Field(min_length=3, max_length=256)
    phone: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=256)
    current_title: str | None = Field(default=None, max_length=256)
    extra_data: dict[str, Any] = Field(default_factory=dict)
    offer_terms_summary: str | None = None
    start_date: date | None = None
    created_by_staff_id: UUID


class EmployeeProfileResponse(BaseModel):
    """Employee profile API representation."""

    employee_id: UUID
    hire_conversion_id: UUID
    vacancy_id: UUID
    candidate_id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    location: str | None
    current_title: str | None
    extra_data: dict[str, Any]
    offer_terms_summary: str | None
    start_date: date | None
    onboarding_id: UUID | None = None
    onboarding_status: OnboardingRunStatus | None = None
    created_by_staff_id: UUID
    created_at: datetime
    updated_at: datetime
