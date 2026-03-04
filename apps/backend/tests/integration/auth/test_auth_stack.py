"""Integration tests for auth stack (service + Redis DAO + JWT)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from hrm_backend.auth.dao.redis_denylist_dao import RedisDenylistDAO
from hrm_backend.auth.services.auth_service import AuthService
from hrm_backend.auth.services.denylist_service import DenylistService
from hrm_backend.auth.services.token_service import TokenService
from hrm_backend.settings import AppSettings


class InMemoryRedis:
    """Minimal Redis-like adapter for integration tests."""

    def __init__(self) -> None:
        """Initialize in-memory key/value storage."""
        self._store: dict[str, bytes] = {}

    def set(self, key: str, value: bytes, ex: int | None = None) -> None:
        """Store binary marker with optional ttl.

        Args:
            key: Redis key.
            value: Stored bytes value.
            ex: Optional ttl in seconds.
        """
        if ex is not None and ex <= 0:
            return
        self._store[key] = value

    def exists(self, key: str) -> int:
        """Check key presence.

        Args:
            key: Redis key.

        Returns:
            int: `1` when key exists, else `0`.
        """
        return 1 if key in self._store else 0


def _build_auth_stack() -> tuple[AuthService, TokenService, RedisDenylistDAO, AppSettings]:
    """Build auth integration stack with real DAO and in-memory Redis adapter.

    Returns:
        tuple[AuthService, TokenService, RedisDenylistDAO, AppSettings]:
            Fully wired stack for integration tests.
    """
    settings = AppSettings(
        jwt_secret="integration-secret-with-minimum-32-bytes",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=604800,
        redis_url="redis://integration:6379/0",
        redis_prefix="auth:integration",
    )
    redis_client = InMemoryRedis()
    dao = RedisDenylistDAO(redis_client=redis_client, key_prefix=settings.redis_prefix)
    denylist_service = DenylistService(
        dao=dao,
        refresh_token_ttl_seconds=settings.refresh_token_ttl_seconds,
    )
    token_service = TokenService(settings=settings)
    auth_service = AuthService(
        token_service=token_service,
        denylist_service=denylist_service,
        settings=settings,
    )
    return auth_service, token_service, dao, settings


def test_refresh_rotation_blocks_old_refresh_via_dao_denylist() -> None:
    """Verify refresh rotation writes denylist entry through Redis DAO."""
    auth_service, token_service, dao, _ = _build_auth_stack()

    first_pair = auth_service.login(subject_id="hr-10", role="hr")
    first_refresh_claims = token_service.decode_refresh_token(first_pair.refresh_token)
    auth_service.refresh(first_pair.refresh_token)

    with pytest.raises(HTTPException) as replay_exc:
        auth_service.refresh(first_pair.refresh_token)

    assert replay_exc.value.status_code == 401
    assert replay_exc.value.detail == "Token revoked"
    assert dao.is_jti_denied(first_refresh_claims.jti) is True


def test_logout_denies_access_token_and_full_sid_session() -> None:
    """Verify logout deny-lists both token jti and sid entries through DAO."""
    auth_service, token_service, dao, settings = _build_auth_stack()
    token_pair = auth_service.login(subject_id="employee-7", role="employee")
    claims = token_service.decode_access_token(token_pair.access_token)

    auth_context = auth_service.authenticate_access_token(token_pair.access_token)
    auth_service.logout(auth_context)

    assert dao.is_jti_denied(claims.jti) is True
    assert dao.is_sid_denied(claims.sid) is True
    assert settings.redis_prefix == "auth:integration"


def test_authenticate_access_token_respects_dao_denylist_marker() -> None:
    """Verify auth stack rejects access token when DAO stores denylist marker."""
    auth_service, token_service, dao, _ = _build_auth_stack()
    token_pair = auth_service.login(subject_id="candidate-15", role="candidate")
    claims = token_service.decode_access_token(token_pair.access_token)

    dao.deny_jti(claims.jti, ttl_seconds=60)

    with pytest.raises(HTTPException) as exc_info:
        auth_service.authenticate_access_token(token_pair.access_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token revoked"
