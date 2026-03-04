"""JWT token creation and validation service using PyJWT."""

from __future__ import annotations

from typing import Final
from uuid import UUID, uuid4

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from pydantic import ValidationError

from hrm_backend.auth.schemas.token_claims import TokenClaims, TokenType
from hrm_backend.core.errors.http import unauthorized
from hrm_backend.core.utils.time import utc_now_epoch
from hrm_backend.settings import AppSettings

_REQUIRED_CLAIMS: Final[tuple[str, ...]] = (
    "sub",
    "role",
    "sid",
    "jti",
    "iat",
    "exp",
    "typ",
)


class TokenService:
    """Service for issuing and validating JWT access and refresh tokens."""

    def __init__(self, settings: AppSettings) -> None:
        """Initialize token service with auth settings."""
        self._settings = settings

    def issue_access_token(self, subject_id: UUID, role: str, session_id: UUID) -> tuple[str, int]:
        """Issue signed access token."""
        now = utc_now_epoch()
        expires_at = now + self._settings.access_token_ttl_seconds
        payload = {
            "sub": str(subject_id),
            "role": role,
            "sid": str(session_id),
            "jti": str(uuid4()),
            "iat": now,
            "exp": expires_at,
            "typ": "access",
        }
        token = jwt.encode(
            payload,
            self._settings.jwt_secret,
            algorithm=self._settings.jwt_algorithm,
        )
        return token, expires_at

    def issue_refresh_token(self, subject_id: UUID, role: str, session_id: UUID) -> tuple[str, int]:
        """Issue signed refresh token."""
        now = utc_now_epoch()
        expires_at = now + self._settings.refresh_token_ttl_seconds
        payload = {
            "sub": str(subject_id),
            "role": role,
            "sid": str(session_id),
            "jti": str(uuid4()),
            "iat": now,
            "exp": expires_at,
            "typ": "refresh",
        }
        token = jwt.encode(
            payload,
            self._settings.jwt_secret,
            algorithm=self._settings.jwt_algorithm,
        )
        return token, expires_at

    def decode_access_token(self, token: str) -> TokenClaims:
        """Decode and validate access token claims."""
        return self._decode_token(token=token, expected_type="access")

    def decode_refresh_token(self, token: str) -> TokenClaims:
        """Decode and validate refresh token claims."""
        return self._decode_token(token=token, expected_type="refresh")

    def _decode_token(self, token: str, expected_type: TokenType) -> TokenClaims:
        """Decode, verify signature, and validate token claims."""
        try:
            raw_claims = jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
                options={"require": list(_REQUIRED_CLAIMS)},
            )
        except ExpiredSignatureError as exc:
            raise unauthorized("Token expired") from exc
        except InvalidTokenError as exc:
            raise unauthorized("Invalid token") from exc

        try:
            claims = TokenClaims.model_validate(raw_claims)
        except ValidationError as exc:
            raise unauthorized("Invalid token claims") from exc

        if claims.typ != expected_type:
            raise unauthorized("Invalid token type")

        return claims
