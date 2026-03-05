"""Response payload schemas for admin endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StaffResponse(BaseModel):
    """Staff account payload for admin APIs."""

    staff_id: UUID
    login: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminStaffListItem(BaseModel):
    """One staff record returned by admin staff list endpoint."""

    staff_id: UUID
    login: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminStaffListResponse(BaseModel):
    """Paginated response payload for admin staff list endpoint."""

    items: list[AdminStaffListItem]
    total: int
    limit: int
    offset: int


class EmployeeRegistrationKeyResponse(BaseModel):
    """Issued employee registration key payload."""

    key_id: UUID
    employee_key: UUID
    target_role: str
    expires_at: datetime
    used_at: datetime | None
    created_by_staff_id: UUID
    created_at: datetime
