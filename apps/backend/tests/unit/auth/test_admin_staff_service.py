"""Unit tests for ADMIN-02 staff list/update business rules in auth service."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.infra.security.password_service import PasswordService
from hrm_backend.auth.services.auth_service import AuthService
from hrm_backend.auth.services.denylist_service import DenylistService
from hrm_backend.auth.services.token_service import TokenService
from hrm_backend.core.models.base import Base
from hrm_backend.settings import AppSettings


class _InMemoryDenylistDAO:
    """Minimal denylist DAO test double required by `DenylistService`."""

    def __init__(self) -> None:
        """Initialize in-memory deny markers."""
        self._denied_jti: set[str] = set()
        self._denied_sid: set[str] = set()

    def deny_jti(self, jti: str, ttl_seconds: int) -> None:
        """Store denied token marker in-memory."""
        if ttl_seconds > 0:
            self._denied_jti.add(jti)

    def deny_sid(self, sid: str, ttl_seconds: int) -> None:
        """Store denied session marker in-memory."""
        if ttl_seconds > 0:
            self._denied_sid.add(sid)

    def is_jti_denied(self, jti: str) -> bool:
        """Return whether token marker is denied."""
        return jti in self._denied_jti

    def is_sid_denied(self, sid: str) -> bool:
        """Return whether session marker is denied."""
        return sid in self._denied_sid


class _InMemoryRegistrationKeyDAO:
    """No-op registration key DAO placeholder for auth service constructor."""

    def create_key(self, **kwargs):  # pragma: no cover - unused in this module
        raise NotImplementedError

    def get_by_employee_key(self, employee_key: str):  # pragma: no cover - unused
        raise NotImplementedError

    def consume_key(self, **kwargs):  # pragma: no cover - unused
        raise NotImplementedError


@pytest.fixture()
def session(tmp_path) -> Session:
    """Provide SQLite session for auth service unit tests."""
    database_url = f"sqlite+pysqlite:///{tmp_path / 'admin_staff_service.db'}"
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db_session:
            yield db_session
    finally:
        engine.dispose()


@pytest.fixture()
def auth_service(session: Session) -> AuthService:
    """Build auth service with real staff DAO and lightweight token/denylist deps."""
    settings = AppSettings(
        jwt_secret="admin-staff-unit-secret-with-minimum-32-bytes",
        jwt_algorithm="HS256",
        access_token_ttl_seconds=900,
        refresh_token_ttl_seconds=604800,
        redis_url="redis://unit:6379/0",
        redis_prefix="auth:deny",
    )
    token_service = TokenService(settings=settings)
    denylist_service = DenylistService(
        dao=_InMemoryDenylistDAO(),
        refresh_token_ttl_seconds=settings.refresh_token_ttl_seconds,
    )
    return AuthService(
        token_service=token_service,
        denylist_service=denylist_service,
        staff_account_dao=StaffAccountDAO(session=session),
        registration_key_dao=_InMemoryRegistrationKeyDAO(),  # type: ignore[arg-type]
        password_service=PasswordService(),
        settings=settings,
    )


def _create_staff(
    auth_service: AuthService,
    *,
    login: str,
    role: str,
    is_active: bool = True,
) -> UUID:
    """Create one staff account through existing admin create flow."""
    response = auth_service.create_staff_account(
        login=login,
        email=f"{login}@example.com",
        password="StrongPassword!123",
        role=role,
        is_active=is_active,
    )
    return response.staff_id


def test_update_staff_rejects_empty_patch(auth_service: AuthService) -> None:
    """Verify empty patch payload is rejected with `empty_patch` reason code."""
    staff_id = _create_staff(auth_service, login="empty-patch-user", role="hr")

    with pytest.raises(HTTPException) as exc_info:
        auth_service.update_staff_account(
            staff_id=staff_id,
            role=None,
            is_active=None,
            actor_subject_id=uuid4(),
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "empty_patch"


def test_update_staff_rejects_unsupported_role(auth_service: AuthService) -> None:
    """Verify unsupported role update is rejected with `unsupported_role`."""
    staff_id = _create_staff(auth_service, login="unsupported-role-user", role="hr")

    with pytest.raises(HTTPException) as exc_info:
        auth_service.update_staff_account(
            staff_id=staff_id,
            role="superadmin",
            is_active=None,
            actor_subject_id=uuid4(),
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "unsupported_role"


def test_update_staff_returns_not_found_for_unknown_staff_id(auth_service: AuthService) -> None:
    """Verify unknown staff identifier returns `staff_not_found`."""
    with pytest.raises(HTTPException) as exc_info:
        auth_service.update_staff_account(
            staff_id=uuid4(),
            role="hr",
            is_active=None,
            actor_subject_id=uuid4(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "staff_not_found"


def test_update_staff_blocks_self_demotion_and_self_disable(auth_service: AuthService) -> None:
    """Verify strict guard blocks self-demotion and self-disable operations."""
    actor_staff_id = _create_staff(auth_service, login="self-guard-admin", role="admin")

    with pytest.raises(HTTPException) as demotion_exc:
        auth_service.update_staff_account(
            staff_id=actor_staff_id,
            role="hr",
            is_active=None,
            actor_subject_id=actor_staff_id,
        )
    assert demotion_exc.value.status_code == 409
    assert demotion_exc.value.detail == "self_modification_forbidden"

    with pytest.raises(HTTPException) as disable_exc:
        auth_service.update_staff_account(
            staff_id=actor_staff_id,
            role=None,
            is_active=False,
            actor_subject_id=actor_staff_id,
        )
    assert disable_exc.value.status_code == 409
    assert disable_exc.value.detail == "self_modification_forbidden"


def test_update_staff_blocks_last_active_admin_disable_and_demotion(
    auth_service: AuthService,
) -> None:
    """Verify strict guard protects last active admin account from disable/demotion."""
    target_admin_id = _create_staff(auth_service, login="last-admin", role="admin")

    with pytest.raises(HTTPException) as demotion_exc:
        auth_service.update_staff_account(
            staff_id=target_admin_id,
            role="hr",
            is_active=None,
            actor_subject_id=uuid4(),
        )
    assert demotion_exc.value.status_code == 409
    assert demotion_exc.value.detail == "last_admin_protection"

    with pytest.raises(HTTPException) as disable_exc:
        auth_service.update_staff_account(
            staff_id=target_admin_id,
            role=None,
            is_active=False,
            actor_subject_id=uuid4(),
        )
    assert disable_exc.value.status_code == 409
    assert disable_exc.value.detail == "last_admin_protection"


def test_update_staff_successfully_updates_role_and_active_state(auth_service: AuthService) -> None:
    """Verify successful staff update path mutates role and active status."""
    _create_staff(auth_service, login="actor-admin", role="admin")
    target_staff_id = _create_staff(auth_service, login="target-hr", role="hr", is_active=True)

    updated_role = auth_service.update_staff_account(
        staff_id=target_staff_id,
        role="manager",
        is_active=None,
        actor_subject_id=uuid4(),
    )
    assert updated_role.role == "manager"
    assert updated_role.is_active is True

    updated_active = auth_service.update_staff_account(
        staff_id=target_staff_id,
        role=None,
        is_active=False,
        actor_subject_id=uuid4(),
    )
    assert updated_active.role == "manager"
    assert updated_active.is_active is False
