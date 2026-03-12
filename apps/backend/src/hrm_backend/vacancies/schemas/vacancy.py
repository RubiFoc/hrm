"""Vacancy API request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VacancyCreateRequest(BaseModel):
    """Input payload for vacancy creation."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1)
    department: str = Field(min_length=1, max_length=128)
    status: str = Field(default="open", min_length=1, max_length=32)
    hiring_manager_login: str | None = Field(default=None, min_length=1, max_length=64)


class VacancyUpdateRequest(BaseModel):
    """Input payload for partial vacancy updates."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = Field(default=None, min_length=1)
    department: str | None = Field(default=None, min_length=1, max_length=128)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    hiring_manager_login: str | None = Field(default=None, min_length=1, max_length=64)


class VacancyResponse(BaseModel):
    """Vacancy API representation."""

    vacancy_id: UUID
    title: str
    description: str
    department: str
    status: str
    hiring_manager_staff_id: UUID | None
    hiring_manager_login: str | None
    created_at: datetime
    updated_at: datetime


class VacancyListResponse(BaseModel):
    """Vacancy list payload."""

    items: list[VacancyResponse]
