"""Authentication and in-memory session lifecycle primitives.

This module implements a bootstrap authentication flow for Phase 1:
- short-lived signed access tokens (Bearer)
- rotating refresh tokens bound to server-side sessions
- session revocation (logout)

Implementation note:
This is intentionally in-memory and process-local to unblock early development
(TASK-01-02). It must be replaced with persistent session storage before
production rollout.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Final

from fastapi import Depends, HTTPException, Request, status

DEFAULT_ACCESS_TOKEN_TTL_SECONDS: Final[int] = 15 * 60
DEFAULT_REFRESH_TOKEN_TTL_SECONDS: Final[int] = 7 * 24 * 60 * 60


def _read_positive_int_env(name: str, default: int) -> int:
    """Read a positive integer value from environment variables.

    Args:
        name: Environment variable name.
        default: Fallback value when variable is missing or invalid.

    Returns:
        int: Positive integer value used for runtime configuration.
    """
    raw = os.getenv(name)
    if raw is None:
        return default

    try:
        parsed = int(raw)
    except ValueError:
        return default

    return parsed if parsed > 0 else default


AUTH_SECRET: Final[str] = os.getenv("HRM_AUTH_SECRET", "hrm-dev-secret-change-me")
ACCESS_TOKEN_TTL_SECONDS: Final[int] = _read_positive_int_env(
    "HRM_ACCESS_TOKEN_TTL_SECONDS",
    DEFAULT_ACCESS_TOKEN_TTL_SECONDS,
)
REFRESH_TOKEN_TTL_SECONDS: Final[int] = _read_positive_int_env(
    "HRM_REFRESH_TOKEN_TTL_SECONDS",
    DEFAULT_REFRESH_TOKEN_TTL_SECONDS,
)


if not AUTH_SECRET.strip():
    raise RuntimeError("HRM_AUTH_SECRET must be non-empty")


@dataclass(frozen=True)
class AuthContext:
    """Validated identity claims extracted from an access token.

    Attributes:
        subject_id: Stable actor identifier (user/candidate/employee id).
        role: Role claim used by RBAC permission checks.
        session_id: Server-side session identifier bound to refresh lifecycle.
        expires_at: UNIX timestamp when access token expires.
    """

    subject_id: str
    role: str
    session_id: str
    expires_at: int


@dataclass
class SessionRecord:
    """Server-side state for refresh token lifecycle and revocation control.

    Attributes:
        session_id: Unique session key.
        subject_id: Authenticated actor id.
        role: Role claim issued for this session.
        refresh_token_hash: SHA-256 hash of the current refresh secret.
        created_at: UNIX timestamp of session creation.
        refresh_expires_at: UNIX timestamp after which refresh is no longer valid.
        revoked_at: UNIX timestamp when session was revoked, if any.
    """

    session_id: str
    subject_id: str
    role: str
    refresh_token_hash: str
    created_at: int
    refresh_expires_at: int
    revoked_at: int | None = None


@dataclass(frozen=True)
class TokenBundle:
    """Token response payload returned by login and refresh endpoints.

    Attributes:
        access_token: Signed bearer token used for API authorization.
        refresh_token: Rotating opaque token used to renew access token.
        session_id: Identifier for the underlying server-side session.
        expires_in: Access token lifetime in seconds.
        token_type: IANA token type, fixed to ``bearer``.
    """

    access_token: str
    refresh_token: str
    session_id: str
    expires_in: int
    token_type: str = "bearer"


class SessionStore:
    """In-memory store for active authentication sessions.

    The store is thread-safe for basic mutation/lookup operations and is scoped
    to the running process. It is suitable for local development and CI checks.
    """

    def __init__(self) -> None:
        """Initialize an empty thread-safe session registry."""
        self._sessions: dict[str, SessionRecord] = {}
        self._lock = threading.RLock()

    def issue_session(self, subject_id: str, role: str) -> TokenBundle:
        """Create a new session and return initial access/refresh tokens.

        Args:
            subject_id: Unique actor identifier.
            role: Actor role claim.

        Returns:
            TokenBundle: Fresh access/refresh tokens tied to the new session.
        """
        now = int(time.time())
        session_id = uuid.uuid4().hex
        refresh_token, refresh_hash = _create_refresh_token(session_id)

        record = SessionRecord(
            session_id=session_id,
            subject_id=subject_id,
            role=role,
            refresh_token_hash=refresh_hash,
            created_at=now,
            refresh_expires_at=now + REFRESH_TOKEN_TTL_SECONDS,
        )

        with self._lock:
            self._sessions[session_id] = record

        access_token = _create_access_token(
            subject_id=subject_id,
            role=role,
            session_id=session_id,
            issued_at=now,
            expires_at=now + ACCESS_TOKEN_TTL_SECONDS,
        )

        return TokenBundle(
            access_token=access_token,
            refresh_token=refresh_token,
            session_id=session_id,
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
        )

    def rotate_refresh_token(self, refresh_token: str) -> TokenBundle:
        """Rotate refresh token and mint a new access token.

        Args:
            refresh_token: Current refresh token in ``<session_id>.<secret>`` format.

        Returns:
            TokenBundle: New token pair for the same active session.

        Raises:
            HTTPException: If refresh token is invalid, expired, or revoked.
        """
        session_id, refresh_secret = _parse_refresh_token(refresh_token)
        presented_hash = _hash_refresh_secret(refresh_secret)

        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                raise _unauthorized("Invalid refresh token")

            now = int(time.time())
            if record.revoked_at is not None:
                raise _unauthorized("Session revoked")
            if record.refresh_expires_at <= now:
                raise _unauthorized("Refresh token expired")
            if not hmac.compare_digest(record.refresh_token_hash, presented_hash):
                raise _unauthorized("Invalid refresh token")

            next_refresh_token, next_refresh_hash = _create_refresh_token(session_id)
            record.refresh_token_hash = next_refresh_hash
            record.refresh_expires_at = now + REFRESH_TOKEN_TTL_SECONDS

            access_token = _create_access_token(
                subject_id=record.subject_id,
                role=record.role,
                session_id=record.session_id,
                issued_at=now,
                expires_at=now + ACCESS_TOKEN_TTL_SECONDS,
            )

        return TokenBundle(
            access_token=access_token,
            refresh_token=next_refresh_token,
            session_id=session_id,
            expires_in=ACCESS_TOKEN_TTL_SECONDS,
        )

    def revoke_session(self, session_id: str) -> None:
        """Revoke an active session.

        Args:
            session_id: Session identifier extracted from a validated access token.

        Side Effects:
            Marks the session as revoked and invalidates refresh token reuse.
        """
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return

            record.revoked_at = int(time.time())
            record.refresh_token_hash = ""

    def validate_access_token(self, access_token: str) -> AuthContext:
        """Validate bearer token signature, claims, and session state.

        Args:
            access_token: Raw bearer token from request headers.

        Returns:
            AuthContext: Verified identity claims used by API authorization.

        Raises:
            HTTPException: If token/session validation fails.
        """
        context = _decode_access_token(access_token)

        with self._lock:
            record = self._sessions.get(context.session_id)
            if record is None:
                raise _unauthorized("Session not found")
            if record.revoked_at is not None:
                raise _unauthorized("Session revoked")
            if record.refresh_expires_at <= int(time.time()):
                raise _unauthorized("Session expired")
            if record.subject_id != context.subject_id or record.role != context.role:
                raise _unauthorized("Session claims mismatch")

        return context


def _unauthorized(detail: str) -> HTTPException:
    """Build a standardized 401 error.

    Args:
        detail: Human-readable error reason.

    Returns:
        HTTPException: Unauthorized response object.
    """
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _b64url_encode(raw: bytes) -> str:
    """Encode bytes to URL-safe Base64 without padding.

    Args:
        raw: Bytes to encode.

    Returns:
        str: URL-safe Base64 string with stripped padding.
    """
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(encoded: str) -> bytes:
    """Decode URL-safe Base64 string with optional missing padding.

    Args:
        encoded: URL-safe Base64 string without required padding.

    Returns:
        bytes: Decoded binary value.

    Raises:
        binascii.Error: If provided value is not valid Base64.
    """
    padding = "=" * ((4 - len(encoded) % 4) % 4)
    return base64.urlsafe_b64decode(f"{encoded}{padding}".encode("ascii"))


def _sign_value(value: str) -> str:
    """Sign a value with HMAC SHA-256 and return URL-safe Base64 digest.

    Args:
        value: Message value to sign.

    Returns:
        str: URL-safe signature string.
    """
    digest = hmac.new(AUTH_SECRET.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def _create_access_token(
    subject_id: str,
    role: str,
    session_id: str,
    issued_at: int,
    expires_at: int,
) -> str:
    """Create signed access token containing identity and expiry claims.

    Args:
        subject_id: Actor identifier claim.
        role: Role claim for RBAC checks.
        session_id: Session identifier claim.
        issued_at: Token issue timestamp.
        expires_at: Token expiry timestamp.

    Returns:
        str: Compact signed token in ``<payload>.<signature>`` format.
    """
    payload = {
        "typ": "access",
        "jti": uuid.uuid4().hex,
        "sub": subject_id,
        "role": role,
        "sid": session_id,
        "iat": issued_at,
        "exp": expires_at,
    }
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload_encoded = _b64url_encode(payload_json.encode("utf-8"))
    signature = _sign_value(payload_encoded)
    return f"{payload_encoded}.{signature}"


def _decode_access_token(access_token: str) -> AuthContext:
    """Decode and validate access token structure, signature, and expiry.

    Args:
        access_token: Raw signed bearer token.

    Returns:
        AuthContext: Identity and session claims.

    Raises:
        HTTPException: If token is malformed, tampered, or expired.
    """
    try:
        payload_encoded, signature = access_token.split(".", maxsplit=1)
    except ValueError as exc:
        raise _unauthorized("Malformed access token") from exc

    expected_signature = _sign_value(payload_encoded)
    if not hmac.compare_digest(signature, expected_signature):
        raise _unauthorized("Invalid access token signature")

    try:
        payload_raw = _b64url_decode(payload_encoded)
        payload_obj = json.loads(payload_raw.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _unauthorized("Malformed access token payload") from exc

    if not isinstance(payload_obj, dict):
        raise _unauthorized("Malformed access token payload")

    token_type = _expect_string_claim(payload_obj, "typ")
    if token_type != "access":
        raise _unauthorized("Unsupported token type")

    subject_id = _expect_string_claim(payload_obj, "sub")
    role = _expect_string_claim(payload_obj, "role")
    session_id = _expect_string_claim(payload_obj, "sid")
    expires_at = _expect_int_claim(payload_obj, "exp")

    if expires_at <= int(time.time()):
        raise _unauthorized("Access token expired")

    return AuthContext(
        subject_id=subject_id,
        role=role,
        session_id=session_id,
        expires_at=expires_at,
    )


def _expect_string_claim(payload: dict[str, object], key: str) -> str:
    """Extract a non-empty string claim from token payload.

    Args:
        payload: Parsed token payload.
        key: Claim name.

    Returns:
        str: Claim value.

    Raises:
        HTTPException: If claim is missing or not a non-empty string.
    """
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _unauthorized(f"Invalid access token claim: {key}")
    return value


def _expect_int_claim(payload: dict[str, object], key: str) -> int:
    """Extract an integer claim from token payload.

    Args:
        payload: Parsed token payload.
        key: Claim name.

    Returns:
        int: Claim value.

    Raises:
        HTTPException: If claim is missing or not an integer.
    """
    value = payload.get(key)
    if not isinstance(value, int):
        raise _unauthorized(f"Invalid access token claim: {key}")
    return value


def _hash_refresh_secret(secret: str) -> str:
    """Build deterministic hash for refresh token secret.

    Args:
        secret: Plain refresh secret value.

    Returns:
        str: SHA-256 hexadecimal digest.
    """
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _create_refresh_token(session_id: str) -> tuple[str, str]:
    """Create a new refresh token and corresponding server-side hash.

    Args:
        session_id: Session identifier to bind refresh token lifecycle.

    Returns:
        tuple[str, str]: Raw refresh token and its hashed secret representation.
    """
    refresh_secret = secrets.token_urlsafe(48)
    refresh_token = f"{session_id}.{refresh_secret}"
    return refresh_token, _hash_refresh_secret(refresh_secret)


def _parse_refresh_token(refresh_token: str) -> tuple[str, str]:
    """Split and validate refresh token format.

    Args:
        refresh_token: Raw token in ``<session_id>.<secret>`` format.

    Returns:
        tuple[str, str]: Session id and refresh secret.

    Raises:
        HTTPException: If token format is invalid.
    """
    try:
        session_id, refresh_secret = refresh_token.split(".", maxsplit=1)
    except ValueError as exc:
        raise _unauthorized("Malformed refresh token") from exc

    if not session_id.strip() or not refresh_secret.strip():
        raise _unauthorized("Malformed refresh token")

    return session_id, refresh_secret


def get_bearer_token(request: Request) -> str:
    """Extract bearer token from ``Authorization`` header.

    Args:
        request: Incoming HTTP request.

    Returns:
        str: Raw bearer token value.

    Raises:
        HTTPException: If header is missing or malformed.
    """
    raw_header = request.headers.get("Authorization")
    if raw_header is None:
        raise _unauthorized("Missing Authorization header: use Bearer token")

    scheme, _, token = raw_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized("Malformed Authorization header: use Bearer <token>")

    return token.strip()


def get_current_auth_context(token: str = Depends(get_bearer_token)) -> AuthContext:
    """Resolve validated authentication context for request-scoped dependencies.

    Args:
        token: Bearer access token extracted from request headers.

    Returns:
        AuthContext: Verified identity claims.
    """
    return SESSION_STORE.validate_access_token(token)


SESSION_STORE = SessionStore()
