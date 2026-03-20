"""Public vacancy list schemas for the careers page."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PublicVacancyListItemResponse(BaseModel):
    """Public-facing vacancy card payload."""

    model_config = ConfigDict(extra="forbid")

    vacancy_id: UUID
    title: str
    description: str
    department: str
    created_at: datetime
    updated_at: datetime


class PublicVacancyListResponse(BaseModel):
    """Public vacancy board payload."""

    model_config = ConfigDict(extra="forbid")

    items: list[PublicVacancyListItemResponse]
