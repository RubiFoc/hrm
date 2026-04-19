"""Schemas for department reference data."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreateRequest(BaseModel):
    """Request payload for creating a department."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)


class DepartmentUpdateRequest(BaseModel):
    """Request payload for patching a department."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=128)


class DepartmentResponse(BaseModel):
    """Department payload returned by API endpoints."""

    model_config = ConfigDict(extra="forbid")

    department_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class DepartmentListItemResponse(BaseModel):
    """Department list item payload."""

    model_config = ConfigDict(extra="forbid")

    department_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class DepartmentListResponse(BaseModel):
    """Paginated list of departments."""

    model_config = ConfigDict(extra="forbid")

    items: list[DepartmentListItemResponse]
    total: int
    limit: int
    offset: int
