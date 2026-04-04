"""Employee-profile request, response, and internal bootstrap schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class EmployeeDirectoryAvatarResponse(BaseModel):
    """Employee avatar metadata exposed in the directory view."""

    avatar_id: UUID
    mime_type: str
    size_bytes: int
    updated_at: datetime


class EmployeeDirectoryListItemResponse(BaseModel):
    """Employee directory list row payload."""

    employee_id: UUID
    full_name: str
    department: str | None
    position_title: str | None
    manager: str | None
    location: str | None
    tenure_in_company: int | None
    subordinates: int | None
    phone: str | None
    email: str | None
    birthday_day_month: str | None
    avatar: EmployeeDirectoryAvatarResponse | None


class EmployeeDirectoryListResponse(BaseModel):
    """Paginated employee directory list payload."""

    items: list[EmployeeDirectoryListItemResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class EmployeeDirectoryProfileResponse(EmployeeDirectoryListItemResponse):
    """Employee directory profile payload."""


class EmployeeProfilePrivacyUpdateRequest(BaseModel):
    """Employee-facing privacy flag update request."""

    model_config = ConfigDict(extra="forbid")

    is_phone_visible: bool | None = None
    is_email_visible: bool | None = None
    is_birthday_visible: bool | None = None

    @model_validator(mode="after")
    def validate_non_nullable(self) -> EmployeeProfilePrivacyUpdateRequest:
        """Reject explicit `null` values for privacy flags."""
        for field_name in ("is_phone_visible", "is_email_visible", "is_birthday_visible"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class EmployeeProfilePrivacySettingsResponse(BaseModel):
    """Employee-facing privacy flag payload."""

    is_phone_visible: bool
    is_email_visible: bool
    is_birthday_visible: bool
