"""Response payload schemas for authentication endpoints."""

from __future__ import annotations

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

