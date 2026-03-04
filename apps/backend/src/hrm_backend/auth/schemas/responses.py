"""Response payload schemas for auth and admin endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """Token pair payload returned by register, login, and refresh operations."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    session_id: UUID


class MeResponse(BaseModel):
    """Authenticated identity payload for `/api/v1/auth/me` endpoint."""

    subject_id: UUID
    role: str
    session_id: UUID
    access_token_expires_at: int


class StaffResponse(BaseModel):
    """Staff account payload for admin APIs."""

    staff_id: UUID
    login: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EmployeeRegistrationKeyResponse(BaseModel):
    """Issued employee registration key payload."""

    key_id: UUID
    employee_key: UUID
    target_role: str
    expires_at: datetime
    used_at: datetime | None
    created_by_staff_id: UUID
    created_at: datetime
