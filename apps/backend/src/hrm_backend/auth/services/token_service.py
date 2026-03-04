"""JWT token creation and validation service using PyJWT."""

from __future__ import annotations

import uuid
from typing import Final

import jwt
from fastapi import HTTPException, status
from jwt import ExpiredSignatureError, InvalidTokenError
from pydantic import ValidationError

from hrm_backend.auth.schemas.token_claims import TokenClaims, TokenType
from hrm_backend.auth.utils.settings import AuthSettings
from hrm_backend.auth.utils.time import utc_now_epoch

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

    def __init__(self, settings: AuthSettings) -> None:
        """Initialize token service with auth settings.

        Args:
            settings: Auth runtime settings.
        """
        self._settings = settings

    def issue_access_token(self, subject_id: str, role: str, session_id: str) -> tuple[str, int]:
        """Issue signed access token.

        Args:
            subject_id: Subject identifier for token claims.
            role: Role claim for RBAC checks.
            session_id: Session identifier shared with refresh token.

        Returns:
            tuple[str, int]: Encoded JWT and expiration timestamp.
        """
        now = utc_now_epoch()
        expires_at = now + self._settings.access_token_ttl_seconds
        payload = {
            "sub": subject_id,
            "role": role,
            "sid": session_id,
            "jti": uuid.uuid4().hex,
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

    def issue_refresh_token(self, subject_id: str, role: str, session_id: str) -> tuple[str, int]:
        """Issue signed refresh token.

        Args:
            subject_id: Subject identifier for token claims.
            role: Role claim mirrored from access token.
            session_id: Session identifier shared with access token.

        Returns:
            tuple[str, int]: Encoded JWT and expiration timestamp.
        """
        now = utc_now_epoch()
        expires_at = now + self._settings.refresh_token_ttl_seconds
        payload = {
            "sub": subject_id,
            "role": role,
            "sid": session_id,
            "jti": uuid.uuid4().hex,
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
        """Decode and validate access token claims.

        Args:
            token: Encoded JWT access token.

        Returns:
            TokenClaims: Validated access token claims.
        """
        return self._decode_token(token=token, expected_type="access")

    def decode_refresh_token(self, token: str) -> TokenClaims:
        """Decode and validate refresh token claims.

        Args:
            token: Encoded JWT refresh token.

        Returns:
            TokenClaims: Validated refresh token claims.
        """
        return self._decode_token(token=token, expected_type="refresh")

    def _decode_token(self, token: str, expected_type: TokenType) -> TokenClaims:
        """Decode, verify signature, and validate token claims.

        Args:
            token: Encoded JWT token.
            expected_type: Expected token type claim.

        Returns:
            TokenClaims: Validated claims object.

        Raises:
            HTTPException: If token is invalid, expired, or wrong type.
        """
        try:
            raw_claims = jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
                options={"require": list(_REQUIRED_CLAIMS)},
            )
        except ExpiredSignatureError as exc:
            raise _unauthorized("Token expired") from exc
        except InvalidTokenError as exc:
            raise _unauthorized("Invalid token") from exc

        try:
            claims = TokenClaims.model_validate(raw_claims)
        except ValidationError as exc:
            raise _unauthorized("Invalid token claims") from exc

        if claims.typ != expected_type:
            raise _unauthorized("Invalid token type")

        return claims


def _unauthorized(detail: str) -> HTTPException:
    """Build standardized unauthorized exception for token operations.

    Args:
        detail: Human-readable error message.

    Returns:
        HTTPException: 401 error object.
    """
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
