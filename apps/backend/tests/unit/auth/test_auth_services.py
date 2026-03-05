"""Unit tests for JWT auth lifecycle and Redis denylist behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from redis.exceptions import RedisError

from hrm_backend.auth.dependencies.auth import get_bearer_token
from hrm_backend.auth.infra.security.password_service import PasswordService
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


@dataclass
class _StaffAccountRow:
    """In-memory staff account row for auth service tests."""

    staff_id: str
    login: str
    email: str
    password_hash: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InMemoryStaffAccountDAO:
    """Simple in-memory staff account DAO test double."""

    def __init__(self) -> None:
        """Initialize in-memory staff account storage."""
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
        """Store and return one in-memory staff row."""
        now = datetime.now(UTC)
        row = _StaffAccountRow(
            staff_id=f"00000000-0000-0000-0000-{len(self._rows) + 1:012d}",
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
        """Find staff account by login/e-mail identifier."""
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
        """Find staff account by normalized login."""
        return next((row for row in self._rows.values() if row.login == login), None)

    def get_by_email(self, email: str) -> _StaffAccountRow | None:
        """Find staff account by normalized e-mail."""
        return next((row for row in self._rows.values() if row.email == email), None)

    def get_by_id(self, staff_id: str) -> _StaffAccountRow | None:
        """Find staff account by identifier."""
        return self._rows.get(staff_id)


class InMemoryRegistrationKeyDAO:
    """No-op registration key DAO used for dependency completeness."""

    def create_key(self, **kwargs):  # pragma: no cover - unused in this test module
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
    """Create one staff account used for login/token lifecycle tests.

    Args:
        auth_service: Auth service instance under test.
        login: Staff login.
        email: Staff e-mail.
        password: Raw staff password.
        role: Staff role.
    """
    password_hash = auth_service._password_service.hash_password(password)
    auth_service._staff_account_dao.create_account(
        login=login,
        email=email,
        password_hash=password_hash,
        role=role,
        is_active=True,
    )


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
    return auth_service, token_service


def test_login_returns_access_and_refresh_jwt_tokens() -> None:
    """Verify login issues valid JWT access/refresh pair with shared session id."""
    auth_service, token_service = _build_auth_service()
    password = "StrongPassword!123"
    _seed_staff_account(
        auth_service,
        login="hr-user-1",
        email="hr-user-1@example.com",
        password=password,
        role="hr",
    )

    token_response = auth_service.login(identifier="hr-user-1", password=password)

    access_claims = token_service.decode_access_token(token_response.access_token)
    refresh_claims = token_service.decode_refresh_token(token_response.refresh_token)

    assert token_response.token_type == "bearer"
    assert token_response.expires_in == 900
    assert access_claims.typ == "access"
    assert refresh_claims.typ == "refresh"
    assert isinstance(access_claims.sub, UUID)
    assert access_claims.sub == refresh_claims.sub
    assert access_claims.role == "hr"
    assert refresh_claims.role == "hr"
    assert access_claims.sid == token_response.session_id == refresh_claims.sid


def test_access_token_validation_passes_when_not_denylisted() -> None:
    """Verify access token is valid when jti and sid are absent from denylist."""
    auth_service, _ = _build_auth_service()
    password = "StrongPassword!123"
    _seed_staff_account(
        auth_service,
        login="employee-1",
        email="employee-1@example.com",
        password=password,
        role="employee",
    )
    token_response = auth_service.login(identifier="employee-1", password=password)

    auth_context = auth_service.authenticate_access_token(token_response.access_token)

    assert isinstance(auth_context.subject_id, UUID)
    assert auth_context.role == "employee"
    assert auth_context.session_id == token_response.session_id


def test_access_token_rejected_when_jti_is_denylisted() -> None:
    """Verify access token is rejected when its jti is denylisted."""
    auth_service, token_service = _build_auth_service()
    password = "StrongPassword!123"
    _seed_staff_account(
        auth_service,
        login="manager-1",
        email="manager-1@example.com",
        password=password,
        role="manager",
    )
    token_response = auth_service.login(identifier="manager-1", password=password)
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
    password = "StrongPassword!123"
    _seed_staff_account(
        auth_service,
        login="employee-1",
        email="employee-1@example.com",
        password=password,
        role="employee",
    )
    token_response = auth_service.login(identifier="employee-1", password=password)
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
    password = "StrongPassword!123"
    _seed_staff_account(
        auth_service,
        login="hr-rot",
        email="hr-rot@example.com",
        password=password,
        role="hr",
    )
    initial_pair = auth_service.login(identifier="hr-rot", password=password)

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
    password = "StrongPassword!123"
    _seed_staff_account(
        auth_service,
        login="leader-1",
        email="leader-1@example.com",
        password=password,
        role="leader",
    )
    token_pair = auth_service.login(identifier="leader-1", password=password)

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
    password = "StrongPassword!123"
    _seed_staff_account(
        auth_service,
        login="hr-2",
        email="hr-2@example.com",
        password=password,
        role="hr",
    )
    token_pair = auth_service.login(identifier="hr-2", password=password)

    with pytest.raises(HTTPException) as exc_info:
        auth_service.authenticate_access_token(token_pair.access_token)

    assert exc_info.value.status_code == 503
    assert "temporarily unavailable" in str(exc_info.value.detail)


def test_get_bearer_token_extracts_token_value() -> None:
    """Verify bearer dependency extracts token from authorization header."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token-value-123")

    assert get_bearer_token(credentials) == "token-value-123"


def test_get_bearer_token_rejects_missing_and_malformed_headers() -> None:
    """Verify bearer dependency rejects missing and malformed auth headers."""
    malformed_credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="abc123")

    with pytest.raises(HTTPException) as missing_exc:
        get_bearer_token(None)
    assert "Missing Authorization header" in str(missing_exc.value.detail)

    with pytest.raises(HTTPException) as malformed_exc:
        get_bearer_token(malformed_credentials)
    assert "Malformed Authorization header" in str(malformed_exc.value.detail)
