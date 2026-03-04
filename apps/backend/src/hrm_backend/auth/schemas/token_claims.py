"""Auth token claim models and request-scoped auth context."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TokenType = Literal["access", "refresh"]


class TokenClaims(BaseModel):
    """JWT claim set used by auth services and dependencies."""

    model_config = ConfigDict(extra="forbid")

    sub: UUID
    role: str = Field(min_length=1, max_length=64)
    sid: UUID
    jti: UUID
    iat: int
    exp: int
    typ: TokenType


class AuthContext(BaseModel):
    """Validated identity context propagated to protected routes."""

    subject_id: UUID
    role: str
    session_id: UUID
    token_id: UUID
    expires_at: int
