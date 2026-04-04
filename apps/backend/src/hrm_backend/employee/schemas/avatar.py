"""Schemas for employee avatar upload and download contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EmployeeAvatarUploadResponse(BaseModel):
    """Metadata payload returned after successful avatar upload."""

    avatar_id: UUID
    employee_id: UUID
    mime_type: str
    size_bytes: int
    updated_at: datetime


class EmployeeAvatarDeleteResponse(BaseModel):
    """Metadata payload returned after successful avatar deletion."""

    employee_id: UUID
    deleted_at: datetime


class EmployeeAvatarDownloadPayload(BaseModel):
    """Internal service payload for avatar download streaming."""

    mime_type: str
    content: bytes
