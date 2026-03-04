"""Request payload schemas for auth endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RoleClaim = Literal["hr", "candidate", "manager", "employee", "leader", "accountant"]


class LoginRequest(BaseModel):
    """Input payload for issuing a fresh JWT token pair.

    Attributes:
        subject_id: Stable actor identifier used as JWT `sub` claim.
        role: Role claim bound to access decisions.
    """

    subject_id: str = Field(min_length=3, max_length=128)
    role: RoleClaim


class RefreshRequest(BaseModel):
    """Input payload for access/refresh token rotation.

    Attributes:
        refresh_token: JWT refresh token to rotate.
    """

    refresh_token: str = Field(min_length=10, max_length=4096)
