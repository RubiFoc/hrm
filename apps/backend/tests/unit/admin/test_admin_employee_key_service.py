"""Unit tests for ADMIN-03 employee key lifecycle rules in admin service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.admin.dao.employee_registration_key_dao import AdminEmployeeRegistrationKeyDAO
from hrm_backend.admin.dao.staff_account_dao import AdminStaffAccountDAO
from hrm_backend.admin.services.admin_service import AdminService
from hrm_backend.auth.infra.security.password_service import PasswordService
from hrm_backend.core.models.base import Base


@pytest.fixture()
def session(tmp_path) -> Session:
    """Provide SQLite session for admin employee-key service tests."""
    database_url = f"sqlite+pysqlite:///{tmp_path / 'admin_employee_key_service.db'}"
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db_session:
            yield db_session
    finally:
        engine.dispose()


@pytest.fixture()
def admin_service(session: Session) -> AdminService:
    """Build admin service with real SQLite DAOs."""
    return AdminService(
        staff_account_dao=AdminStaffAccountDAO(session=session),
        employee_registration_key_dao=AdminEmployeeRegistrationKeyDAO(session=session),
        password_service=PasswordService(),
    )


def _create_staff(
    admin_service: AdminService,
    *,
    login: str,
    role: str,
) -> UUID:
    """Create one staff account through admin create flow."""
    response = admin_service.create_staff_account(
        login=login,
        email=f"{login}@example.com",
        password="StrongPassword!123",
        role=role,
        is_active=True,
    )
    return response.staff_id


def _mark_key_used(admin_service: AdminService, key_id: UUID) -> None:
    """Set `used_at` timestamp for one key row in storage."""
    entity = admin_service._employee_registration_key_dao.get_by_id(str(key_id))
    assert entity is not None
    entity.used_at = datetime.now(UTC)
    admin_service._employee_registration_key_dao._session.add(entity)
    admin_service._employee_registration_key_dao._session.commit()


def _mark_key_expired(admin_service: AdminService, key_id: UUID) -> None:
    """Move key expiration timestamp to the past for guard testing."""
    entity = admin_service._employee_registration_key_dao.get_by_id(str(key_id))
    assert entity is not None
    entity.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    admin_service._employee_registration_key_dao._session.add(entity)
    admin_service._employee_registration_key_dao._session.commit()


def test_list_employee_keys_resolves_statuses(admin_service: AdminService) -> None:
    """Verify list use-case computes active/used/expired/revoked statuses."""
    issuer_id = _create_staff(admin_service, login="issuer-admin", role="admin")

    active = admin_service.create_employee_key(
        target_role="employee",
        created_by_staff_id=issuer_id,
        ttl_seconds=3600,
    )
    used = admin_service.create_employee_key(
        target_role="manager",
        created_by_staff_id=issuer_id,
        ttl_seconds=3600,
    )
    expired = admin_service.create_employee_key(
        target_role="leader",
        created_by_staff_id=issuer_id,
        ttl_seconds=3600,
    )
    revoked = admin_service.create_employee_key(
        target_role="accountant",
        created_by_staff_id=issuer_id,
        ttl_seconds=3600,
    )

    _mark_key_used(admin_service, used.key_id)
    _mark_key_expired(admin_service, expired.key_id)
    admin_service.revoke_employee_key(key_id=revoked.key_id, revoked_by_staff_id=issuer_id)

    listed = admin_service.list_employee_keys(limit=20, offset=0)
    statuses = {item.key_id: item.status for item in listed.items}

    assert statuses[active.key_id] == "active"
    assert statuses[used.key_id] == "used"
    assert statuses[expired.key_id] == "expired"
    assert statuses[revoked.key_id] == "revoked"


def test_revoke_employee_key_rejects_not_found(admin_service: AdminService) -> None:
    """Verify revoke returns `key_not_found` for unknown key identifiers."""
    with pytest.raises(HTTPException) as exc_info:
        admin_service.revoke_employee_key(
            key_id=uuid4(),
            revoked_by_staff_id=uuid4(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "key_not_found"


def test_revoke_employee_key_rejects_already_used_expired_or_revoked(
    admin_service: AdminService,
) -> None:
    """Verify revoke guard returns stable reason codes for non-revocable states."""
    issuer_id = _create_staff(admin_service, login="issuer-guard", role="admin")

    used_key = admin_service.create_employee_key(
        target_role="employee",
        created_by_staff_id=issuer_id,
        ttl_seconds=3600,
    )
    expired_key = admin_service.create_employee_key(
        target_role="employee",
        created_by_staff_id=issuer_id,
        ttl_seconds=3600,
    )
    revoked_key = admin_service.create_employee_key(
        target_role="employee",
        created_by_staff_id=issuer_id,
        ttl_seconds=3600,
    )

    _mark_key_used(admin_service, used_key.key_id)
    _mark_key_expired(admin_service, expired_key.key_id)
    admin_service.revoke_employee_key(key_id=revoked_key.key_id, revoked_by_staff_id=issuer_id)

    with pytest.raises(HTTPException) as used_exc:
        admin_service.revoke_employee_key(key_id=used_key.key_id, revoked_by_staff_id=issuer_id)
    assert used_exc.value.status_code == 409
    assert used_exc.value.detail == "key_already_used"

    with pytest.raises(HTTPException) as expired_exc:
        admin_service.revoke_employee_key(key_id=expired_key.key_id, revoked_by_staff_id=issuer_id)
    assert expired_exc.value.status_code == 409
    assert expired_exc.value.detail == "key_already_expired"

    with pytest.raises(HTTPException) as revoked_exc:
        admin_service.revoke_employee_key(key_id=revoked_key.key_id, revoked_by_staff_id=issuer_id)
    assert revoked_exc.value.status_code == 409
    assert revoked_exc.value.detail == "key_already_revoked"


def test_revoke_employee_key_returns_revoked_payload(admin_service: AdminService) -> None:
    """Verify revoke succeeds for active keys and returns revoked status payload."""
    issuer_id = _create_staff(admin_service, login="issuer-success", role="admin")

    key = admin_service.create_employee_key(
        target_role="employee",
        created_by_staff_id=issuer_id,
        ttl_seconds=3600,
    )
    result = admin_service.revoke_employee_key(
        key_id=key.key_id,
        revoked_by_staff_id=issuer_id,
    )

    assert result.key_id == key.key_id
    assert result.status == "revoked"
    assert result.revoked_at is not None
    assert result.revoked_by_staff_id == issuer_id
