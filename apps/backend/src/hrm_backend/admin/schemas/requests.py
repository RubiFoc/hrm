"""Request payload schemas for admin endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

StaffRoleClaim = Literal["admin", "hr", "manager", "employee", "leader", "accountant"]
EmployeeKeyStatusClaim = Literal["active", "used", "expired", "revoked"]


class AdminCreateStaffRequest(BaseModel):
    """Input payload for admin-managed direct staff account creation."""

    model_config = ConfigDict(extra="forbid")

    login: str = Field(min_length=3, max_length=64)
    email: str = Field(min_length=3, max_length=256)
    password: str = Field(min_length=12, max_length=256)
    role: StaffRoleClaim
    is_active: bool = True

    @field_validator("login")
    @classmethod
    def normalize_login(cls, value: str) -> str:
        """Normalize login to lower-case trimmed format."""
        return value.strip().lower()

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Normalize email and perform basic syntax check."""
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Invalid email format")
        return normalized


class AdminStaffUpdateRequest(BaseModel):
    """Input payload for admin-managed staff role/active-state updates."""

    model_config = ConfigDict(extra="forbid")

    role: StaffRoleClaim | None = None
    is_active: bool | None = None


class AdminCreateEmployeeKeyRequest(BaseModel):
    """Input payload for employee registration key issuance."""

    model_config = ConfigDict(extra="forbid")

    target_role: StaffRoleClaim
    ttl_seconds: int = Field(default=7 * 24 * 60 * 60, gt=0, le=30 * 24 * 60 * 60)
