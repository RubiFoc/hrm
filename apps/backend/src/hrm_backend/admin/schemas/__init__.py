"""Pydantic schemas for admin API requests and responses."""

from hrm_backend.admin.schemas.requests import (
    AdminCreateEmployeeKeyRequest,
    AdminCreateStaffRequest,
    AdminStaffUpdateRequest,
    EmployeeKeyStatusClaim,
    StaffRoleClaim,
)
from hrm_backend.admin.schemas.responses import (
    AdminEmployeeKeyListItem,
    AdminEmployeeKeyListResponse,
    AdminStaffListItem,
    AdminStaffListResponse,
    EmployeeRegistrationKeyResponse,
    EmployeeRegistrationKeyStatus,
    StaffResponse,
)

__all__ = [
    "StaffRoleClaim",
    "EmployeeKeyStatusClaim",
    "AdminCreateStaffRequest",
    "AdminStaffUpdateRequest",
    "AdminCreateEmployeeKeyRequest",
    "StaffResponse",
    "AdminStaffListItem",
    "AdminStaffListResponse",
    "EmployeeRegistrationKeyResponse",
    "EmployeeRegistrationKeyStatus",
    "AdminEmployeeKeyListItem",
    "AdminEmployeeKeyListResponse",
]
