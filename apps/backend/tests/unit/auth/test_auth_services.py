"""Unit tests for JWT auth lifecycle and Redis denylist behavior."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from redis.exceptions import RedisError
from starlette.requests import Request

from hrm_backend.auth.dependencies.auth import get_bearer_token
from hrm_backend.auth.services.auth_service import AuthService
from hrm_backend.auth.services.denylist_service import DenylistService
from hrm_backend.auth.services.token_service import TokenService
from hrm_backend.settings import AppSettings


class InMemoryDenylistDAO:
    """Simple denylist DAO test double for deterministic auth service tests."""

    def __init__(self) -> None:
        """Initialize in-memory denylist markers."""
        self.denied_jti: set[str] = set()
        self.denied_sid: set[str] = set()

    def deny_jti(self, jti: str, ttl_seconds: int) -> None:
        """Mark token id as denied in-memory.

        Args:
            jti: Token id claim.
            ttl_seconds: TTL in seconds.
        """
        if ttl_seconds > 0:
            self.denied_jti.add(jti)

    def deny_sid(self, sid: str, ttl_seconds: int) -> None:
        """Mark session id as denied in-memory.

        Args:
            sid: Session id claim.
            ttl_seconds: TTL in seconds.
        """
        if ttl_seconds > 0:
            self.denied_sid.add(sid)

    def is_jti_denied(self, jti: str) -> bool:
        """Check whether token id is denied.

        Args:
            jti: Token id claim.

        Returns:
            bool: `True` if denied.
        """
        return jti in self.denied_jti

    def is_sid_denied(self, sid: str) -> bool:
        """Check whether session id is denied.

        Args:
            sid: Session id claim.

        Returns:
            bool: `True` if denied.
        """
        return sid in self.denied_sid


class FailingReadDenylistDAO(InMemoryDenylistDAO):
    """Denylist DAO test double that simulates Redis read failures."""

    def is_jti_denied(self, jti: str) -> bool:
        """Raise Redis error on denylist reads.

        Args:
            jti: Token id claim.

        Raises:
            RedisError: Always raised to test fail-closed behavior.
        """
        raise RedisError("redis unavailable")


def _request_with_headers(headers: dict[str, str]) -> Request:
    """Build minimal Starlette request object with provided HTTP headers.

    Args:
        headers: Header map represented as plain string pairs.

    Returns:
        Request: Request object suitable for dependency function testing.
    """
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in headers.items()
        ],
    }
    return Request(scope)


def _build_settings() -> AppSettings:
    """Build deterministic auth settings for tests.

    Returns:
        AppSettings: Test-specific settings object.
    """
    return AppSettings(
        jwt_secret="unit-test-secret-with-minimum-32-bytes",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=604800,
        redis_url="redis://test:6379/0",
        redis_prefix="auth:deny",
    )


def _build_auth_service(dao: InMemoryDenylistDAO | None = None) -> tuple[AuthService, TokenService]:
    """Create auth service with deterministic dependencies for unit tests.

    Args:
        dao: Optional denylist DAO test double.

    Returns:
        tuple[AuthService, TokenService]: Auth service and token service pair.
    """
    settings = _build_settings()
    token_service = TokenService(settings=settings)
    denylist_dao = InMemoryDenylistDAO() if dao is None else dao
    denylist_service = DenylistService(
        dao=denylist_dao,
        refresh_token_ttl_seconds=settings.refresh_token_ttl_seconds,
    )
    auth_service = AuthService(
        token_service=token_service,
        denylist_service=denylist_service,
        settings=settings,
    )
    return auth_service, token_service


def test_login_returns_access_and_refresh_jwt_tokens() -> None:
    """Verify login issues valid JWT access/refresh pair with shared session id."""
    auth_service, token_service = _build_auth_service()

    token_response = auth_service.login(subject_id="hr-user-1", role="hr")

    access_claims = token_service.decode_access_token(token_response.access_token)
    refresh_claims = token_service.decode_refresh_token(token_response.refresh_token)

    assert token_response.token_type == "bearer"
    assert token_response.expires_in == 900
    assert access_claims.typ == "access"
    assert refresh_claims.typ == "refresh"
    assert access_claims.sub == "hr-user-1"
    assert refresh_claims.sub == "hr-user-1"
    assert access_claims.role == "hr"
    assert refresh_claims.role == "hr"
    assert access_claims.sid == token_response.session_id == refresh_claims.sid


def test_access_token_validation_passes_when_not_denylisted() -> None:
    """Verify access token is valid when jti and sid are absent from denylist."""
    auth_service, _ = _build_auth_service()
    token_response = auth_service.login(subject_id="candidate-1", role="candidate")

    auth_context = auth_service.authenticate_access_token(token_response.access_token)

    assert auth_context.subject_id == "candidate-1"
    assert auth_context.role == "candidate"
    assert auth_context.session_id == token_response.session_id


def test_access_token_rejected_when_jti_is_denylisted() -> None:
    """Verify access token is rejected when its jti is denylisted."""
    auth_service, token_service = _build_auth_service()
    token_response = auth_service.login(subject_id="candidate-2", role="candidate")
    access_claims = token_service.decode_access_token(token_response.access_token)

    auth_service._denylist_service.deny_jti_until_exp(access_claims.jti, access_claims.exp)

    with pytest.raises(HTTPException) as exc_info:
        auth_service.authenticate_access_token(token_response.access_token)

    assert access_claims.jti
    assert exc_info.value.status_code == 401
    assert "Token revoked" in str(exc_info.value.detail)


def test_access_token_rejected_when_sid_is_denylisted() -> None:
    """Verify access token is rejected when session id is denylisted."""
    auth_service, token_service = _build_auth_service()
    token_response = auth_service.login(subject_id="employee-1", role="employee")
    access_claims = token_service.decode_access_token(token_response.access_token)

    auth_service._denylist_service.deny_sid_for_refresh_window(access_claims.sid)

    with pytest.raises(HTTPException) as exc_info:
        auth_service.authenticate_access_token(token_response.access_token)

    assert access_claims.sid == token_response.session_id
    assert exc_info.value.status_code == 401
    assert "Token revoked" in str(exc_info.value.detail)


def test_refresh_rotates_pair_and_rejects_old_refresh_token() -> None:
    """Verify refresh rotates token pair and rejects replay of old refresh token."""
    auth_service, _ = _build_auth_service()
    initial_pair = auth_service.login(subject_id="hr-rot", role="hr")

    rotated_pair = auth_service.refresh(initial_pair.refresh_token)

    assert rotated_pair.refresh_token != initial_pair.refresh_token
    assert rotated_pair.access_token != initial_pair.access_token
    assert rotated_pair.session_id == initial_pair.session_id

    with pytest.raises(HTTPException) as exc_info:
        auth_service.refresh(initial_pair.refresh_token)

    assert exc_info.value.status_code == 401
    assert "Token revoked" in str(exc_info.value.detail)


def test_logout_invalidates_access_and_refresh_by_sid() -> None:
    """Verify logout denylists access jti and full sid refresh window."""
    auth_service, _ = _build_auth_service()
    token_pair = auth_service.login(subject_id="leader-1", role="leader")

    auth_context = auth_service.authenticate_access_token(token_pair.access_token)
    auth_service.logout(auth_context)

    with pytest.raises(HTTPException) as access_exc:
        auth_service.authenticate_access_token(token_pair.access_token)
    assert access_exc.value.status_code == 401
    assert "Token revoked" in str(access_exc.value.detail)

    with pytest.raises(HTTPException) as refresh_exc:
        auth_service.refresh(token_pair.refresh_token)
    assert refresh_exc.value.status_code == 401
    assert "Token revoked" in str(refresh_exc.value.detail)


def test_fail_closed_when_redis_denylist_is_unavailable() -> None:
    """Verify token validation fails closed when denylist backend is unavailable."""
    auth_service, _ = _build_auth_service(dao=FailingReadDenylistDAO())
    token_pair = auth_service.login(subject_id="candidate-3", role="candidate")

    with pytest.raises(HTTPException) as exc_info:
        auth_service.authenticate_access_token(token_pair.access_token)

    assert exc_info.value.status_code == 503
    assert "temporarily unavailable" in str(exc_info.value.detail)


def test_get_bearer_token_extracts_token_value() -> None:
    """Verify bearer dependency extracts token from authorization header."""
    request = _request_with_headers({"Authorization": "Bearer token-value-123"})

    assert get_bearer_token(request) == "token-value-123"


def test_get_bearer_token_rejects_missing_and_malformed_headers() -> None:
    """Verify bearer dependency rejects missing and malformed auth headers."""
    missing_header_request = _request_with_headers({})
    malformed_header_request = _request_with_headers({"Authorization": "Basic abc123"})

    with pytest.raises(HTTPException) as missing_exc:
        get_bearer_token(missing_header_request)
    assert "Missing Authorization header" in str(missing_exc.value.detail)

    with pytest.raises(HTTPException) as malformed_exc:
        get_bearer_token(malformed_header_request)
    assert "Malformed Authorization header" in str(malformed_exc.value.detail)
