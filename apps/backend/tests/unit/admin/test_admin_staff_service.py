"""Unit tests for ADMIN-02 staff list/update business rules in admin service."""

from __future__ import annotations

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
    """Provide SQLite session for admin service unit tests."""
    database_url = f"sqlite+pysqlite:///{tmp_path / 'admin_staff_service.db'}"
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
    is_active: bool = True,
) -> UUID:
    """Create one staff account through admin create flow."""
    response = admin_service.create_staff_account(
        login=login,
        email=f"{login}@example.com",
        password="StrongPassword!123",
        role=role,
        is_active=is_active,
    )
    return response.staff_id


def test_update_staff_rejects_empty_patch(admin_service: AdminService) -> None:
    """Verify empty patch payload is rejected with `empty_patch` reason code."""
    staff_id = _create_staff(admin_service, login="empty-patch-user", role="hr")

    with pytest.raises(HTTPException) as exc_info:
        admin_service.update_staff_account(
            staff_id=staff_id,
            role=None,
            is_active=None,
            actor_subject_id=uuid4(),
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "empty_patch"


def test_update_staff_rejects_unsupported_role(admin_service: AdminService) -> None:
    """Verify unsupported role update is rejected with `unsupported_role`."""
    staff_id = _create_staff(admin_service, login="unsupported-role-user", role="hr")

    with pytest.raises(HTTPException) as exc_info:
        admin_service.update_staff_account(
            staff_id=staff_id,
            role="superadmin",
            is_active=None,
            actor_subject_id=uuid4(),
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "unsupported_role"


def test_update_staff_returns_not_found_for_unknown_staff_id(admin_service: AdminService) -> None:
    """Verify unknown staff identifier returns `staff_not_found`."""
    with pytest.raises(HTTPException) as exc_info:
        admin_service.update_staff_account(
            staff_id=uuid4(),
            role="hr",
            is_active=None,
            actor_subject_id=uuid4(),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "staff_not_found"


def test_update_staff_blocks_self_demotion_and_self_disable(admin_service: AdminService) -> None:
    """Verify strict guard blocks self-demotion and self-disable operations."""
    actor_staff_id = _create_staff(admin_service, login="self-guard-admin", role="admin")

    with pytest.raises(HTTPException) as demotion_exc:
        admin_service.update_staff_account(
            staff_id=actor_staff_id,
            role="hr",
            is_active=None,
            actor_subject_id=actor_staff_id,
        )
    assert demotion_exc.value.status_code == 409
    assert demotion_exc.value.detail == "self_modification_forbidden"

    with pytest.raises(HTTPException) as disable_exc:
        admin_service.update_staff_account(
            staff_id=actor_staff_id,
            role=None,
            is_active=False,
            actor_subject_id=actor_staff_id,
        )
    assert disable_exc.value.status_code == 409
    assert disable_exc.value.detail == "self_modification_forbidden"


def test_update_staff_blocks_last_active_admin_disable_and_demotion(
    admin_service: AdminService,
) -> None:
    """Verify strict guard protects last active admin account from disable/demotion."""
    target_admin_id = _create_staff(admin_service, login="last-admin", role="admin")

    with pytest.raises(HTTPException) as demotion_exc:
        admin_service.update_staff_account(
            staff_id=target_admin_id,
            role="hr",
            is_active=None,
            actor_subject_id=uuid4(),
        )
    assert demotion_exc.value.status_code == 409
    assert demotion_exc.value.detail == "last_admin_protection"

    with pytest.raises(HTTPException) as disable_exc:
        admin_service.update_staff_account(
            staff_id=target_admin_id,
            role=None,
            is_active=False,
            actor_subject_id=uuid4(),
        )
    assert disable_exc.value.status_code == 409
    assert disable_exc.value.detail == "last_admin_protection"


def test_update_staff_successfully_updates_role_and_active_state(
    admin_service: AdminService,
) -> None:
    """Verify successful staff update path mutates role and active status."""
    _create_staff(admin_service, login="actor-admin", role="admin")
    target_staff_id = _create_staff(admin_service, login="target-hr", role="hr", is_active=True)

    updated_role = admin_service.update_staff_account(
        staff_id=target_staff_id,
        role="manager",
        is_active=None,
        actor_subject_id=uuid4(),
    )
    assert updated_role.role == "manager"
    assert updated_role.is_active is True

    updated_active = admin_service.update_staff_account(
        staff_id=target_staff_id,
        role=None,
        is_active=False,
        actor_subject_id=uuid4(),
    )
    assert updated_active.role == "manager"
    assert updated_active.is_active is False
