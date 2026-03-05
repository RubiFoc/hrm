"""Pydantic schemas for auth/admin requests, responses, and token claims."""

from hrm_backend.auth.schemas.requests import (
    AdminCreateEmployeeKeyRequest,
    AdminCreateStaffRequest,
    AdminStaffUpdateRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from hrm_backend.auth.schemas.responses import (
    AdminStaffListItem,
    AdminStaffListResponse,
    EmployeeRegistrationKeyResponse,
    MeResponse,
    StaffResponse,
    TokenResponse,
)
from hrm_backend.auth.schemas.token_claims import AuthContext, TokenClaims

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "RefreshRequest",
    "AdminCreateStaffRequest",
    "AdminStaffUpdateRequest",
    "AdminCreateEmployeeKeyRequest",
    "TokenResponse",
    "MeResponse",
    "StaffResponse",
    "AdminStaffListItem",
    "AdminStaffListResponse",
    "EmployeeRegistrationKeyResponse",
    "TokenClaims",
    "AuthContext",
]
