"""Integration tests for auth stack (service + Redis DAO + JWT)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from hrm_backend.auth.dao.redis_denylist_dao import RedisDenylistDAO
from hrm_backend.auth.infra.security.password_service import PasswordService
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


@dataclass
class _StaffAccountRow:
    """In-memory staff account row used by auth integration tests."""

    staff_id: str
    login: str
    email: str
    password_hash: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InMemoryStaffAccountDAO:
    """In-memory staff DAO for auth integration tests."""

    def __init__(self) -> None:
        """Initialize account storage."""
        self._rows: dict[str, _StaffAccountRow] = {}

    def create_account(
        self,
        *,
        login: str,
        email: str,
        password_hash: str,
        role: str,
        is_active: bool = True,
    ) -> _StaffAccountRow:
        """Create one account row."""
        now = datetime.now(UTC)
        row = _StaffAccountRow(
            staff_id=f"10000000-0000-0000-0000-{len(self._rows) + 1:012d}",
            login=login,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
        self._rows[row.staff_id] = row
        return row

    def get_by_identifier(self, identifier: str) -> _StaffAccountRow | None:
        """Find account by login or e-mail identifier."""
        normalized = identifier.strip().lower()
        return next(
            (
                row
                for row in self._rows.values()
                if row.login == normalized or row.email == normalized
            ),
            None,
        )

    def get_by_login(self, login: str) -> _StaffAccountRow | None:
        """Find account by login."""
        return next((row for row in self._rows.values() if row.login == login), None)

    def get_by_email(self, email: str) -> _StaffAccountRow | None:
        """Find account by e-mail."""
        return next((row for row in self._rows.values() if row.email == email), None)

    def get_by_id(self, staff_id: str) -> _StaffAccountRow | None:
        """Find account by id."""
        return self._rows.get(staff_id)


class InMemoryRegistrationKeyDAO:
    """No-op registration key DAO required by auth service constructor."""

    def create_key(self, **kwargs):  # pragma: no cover - unused in this module
        raise NotImplementedError

    def get_by_employee_key(self, employee_key: str):  # pragma: no cover - unused
        raise NotImplementedError

    def consume_key(self, **kwargs):  # pragma: no cover - unused
        raise NotImplementedError


def _seed_staff_account(
    auth_service: AuthService,
    *,
    login: str,
    email: str,
    password: str,
    role: str,
) -> None:
    """Create one account row used by login-centric integration tests."""
    auth_service.create_staff_account(
        login=login,
        email=email,
        password=password,
        role=role,
        is_active=True,
    )


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
    staff_account_dao = InMemoryStaffAccountDAO()
    registration_key_dao = InMemoryRegistrationKeyDAO()
    password_service = PasswordService()
    auth_service = AuthService(
        token_service=token_service,
        denylist_service=denylist_service,
        staff_account_dao=staff_account_dao,  # type: ignore[arg-type]
        registration_key_dao=registration_key_dao,  # type: ignore[arg-type]
        password_service=password_service,
        settings=settings,
    )
    return auth_service, token_service, dao, settings


def test_refresh_rotation_blocks_old_refresh_via_dao_denylist() -> None:
    """Verify refresh rotation writes denylist entry through Redis DAO."""
    auth_service, token_service, dao, _ = _build_auth_stack()
    password = "IntegrationPassword!123"
    _seed_staff_account(
        auth_service,
        login="hr-10",
        email="hr-10@example.com",
        password=password,
        role="hr",
    )

    first_pair = auth_service.login(identifier="hr-10", password=password)
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
    password = "IntegrationPassword!123"
    _seed_staff_account(
        auth_service,
        login="employee-7",
        email="employee-7@example.com",
        password=password,
        role="employee",
    )
    token_pair = auth_service.login(identifier="employee-7", password=password)
    claims = token_service.decode_access_token(token_pair.access_token)

    auth_context = auth_service.authenticate_access_token(token_pair.access_token)
    auth_service.logout(auth_context)

    assert dao.is_jti_denied(claims.jti) is True
    assert dao.is_sid_denied(claims.sid) is True
    assert settings.redis_prefix == "auth:integration"


def test_authenticate_access_token_respects_dao_denylist_marker() -> None:
    """Verify auth stack rejects access token when DAO stores denylist marker."""
    auth_service, token_service, dao, _ = _build_auth_stack()
    password = "IntegrationPassword!123"
    _seed_staff_account(
        auth_service,
        login="leader-15",
        email="leader-15@example.com",
        password=password,
        role="leader",
    )
    token_pair = auth_service.login(identifier="leader-15", password=password)
    claims = token_service.decode_access_token(token_pair.access_token)

    dao.deny_jti(claims.jti, ttl_seconds=60)

    with pytest.raises(HTTPException) as exc_info:
        auth_service.authenticate_access_token(token_pair.access_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token revoked"
