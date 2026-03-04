"""Auth token claim models and request-scoped auth context."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TokenType = Literal["access", "refresh"]


class TokenClaims(BaseModel):
    """JWT claim set used by auth services and dependencies.

    Attributes:
        sub: Subject identifier for authenticated actor.
        role: Role claim used by RBAC checks.
        sid: Session identifier used for denylist-based invalidation.
        jti: Unique token identifier used for replay and revocation checks.
        iat: Token issue timestamp (UNIX seconds).
        exp: Token expiry timestamp (UNIX seconds).
        typ: Token type marker (`access` or `refresh`).
    """

    model_config = ConfigDict(extra="forbid")

    sub: str = Field(min_length=1, max_length=128)
    role: str = Field(min_length=1, max_length=64)
    sid: str = Field(min_length=1, max_length=64)
    jti: str = Field(min_length=1, max_length=64)
    iat: int
    exp: int
    typ: TokenType


class AuthContext(BaseModel):
    """Validated identity context propagated to protected routes.

    Attributes:
        subject_id: Subject identifier from access token.
        role: Role claim from access token.
        session_id: Session identifier from access token.
        token_id: Access token `jti` value.
        expires_at: Access token expiration timestamp (UNIX seconds).
    """

    subject_id: str
    role: str
    session_id: str
    token_id: str
    expires_at: int
