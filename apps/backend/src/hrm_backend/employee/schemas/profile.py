"""Employee-profile request, response, and internal bootstrap schemas."""

from __future__ import annotations

from dataclasses import dataclass
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
    avatar_url: str | None = None
    avatar_updated_at: datetime | None = None
    is_dismissed: bool = False
    onboarding_id: UUID | None = None
    onboarding_status: OnboardingRunStatus | None = None
    created_by_staff_id: UUID
    created_at: datetime
    updated_at: datetime


class EmployeeDirectoryListItemResponse(BaseModel):
    """Directory-card representation for one employee profile visible to employees."""

    employee_id: UUID
    full_name: str
    email: str
    phone: str | None
    location: str | None
    position_title: str | None
    department: str | None
    manager: str | None
    subordinates: int | None
    birthday_day_month: str | None
    tenure_in_company_months: int | None = Field(default=None, ge=0)
    avatar_url: str | None
    avatar_updated_at: datetime | None
    is_dismissed: bool


class EmployeeDirectoryListResponse(BaseModel):
    """Paginated employee-directory payload."""

    items: list[EmployeeDirectoryListItemResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class EmployeeDirectoryProfileResponse(BaseModel):
    """Detailed employee-directory profile payload for cross-employee visibility."""

    employee_id: UUID
    full_name: str
    email: str
    phone: str | None
    location: str | None
    position_title: str | None
    department: str | None
    manager: str | None
    subordinates: int | None
    birthday_day_month: str | None
    tenure_in_company_months: int | None = Field(default=None, ge=0)
    avatar_url: str | None
    avatar_updated_at: datetime | None
    is_dismissed: bool


class EmployeeAvatarUploadResponse(BaseModel):
    """Response payload returned after successful avatar upload/update."""

    employee_id: UUID
    avatar_url: str
    avatar_updated_at: datetime


@dataclass(frozen=True)
class EmployeeAvatarDownloadPayload:
    """Internal service payload for employee avatar streaming."""

    filename: str
    mime_type: str
    content: bytes
