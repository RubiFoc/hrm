"""Pydantic schemas for admin API requests and responses."""

from hrm_backend.admin.schemas.requests import (
    AdminCreateEmployeeKeyRequest,
    AdminCreateStaffRequest,
    AdminStaffUpdateRequest,
    StaffRoleClaim,
)
from hrm_backend.admin.schemas.responses import (
    AdminStaffListItem,
    AdminStaffListResponse,
    EmployeeRegistrationKeyResponse,
    StaffResponse,
)

__all__ = [
    "StaffRoleClaim",
    "AdminCreateStaffRequest",
    "AdminStaffUpdateRequest",
    "AdminCreateEmployeeKeyRequest",
    "StaffResponse",
    "AdminStaffListItem",
    "AdminStaffListResponse",
    "EmployeeRegistrationKeyResponse",
]
