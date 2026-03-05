"""Unit tests for admin staff account DAO list/filter/update behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from time import sleep

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.admin.dao.staff_account_dao import AdminStaffAccountDAO
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.core.models.base import Base


@pytest.fixture()
def session(tmp_path) -> Session:
    """Provide temporary SQLite session for DAO tests."""
    database_url = f"sqlite+pysqlite:///{tmp_path / 'staff_account_dao.db'}"
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db_session:
            yield db_session
    finally:
        engine.dispose()


def _insert_account(
    session: Session,
    *,
    staff_id: str,
    login: str,
    email: str,
    role: str,
    is_active: bool,
    created_at: datetime,
) -> StaffAccount:
    """Insert deterministic staff account row for list/filter assertions."""
    entity = StaffAccount(
        staff_id=staff_id,
        login=login,
        email=email,
        password_hash="hash",
        role=role,
        is_active=is_active,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return entity


def test_list_and_count_apply_filters_and_pagination(session: Session) -> None:
    """Verify DAO applies search/role/is_active filters with deterministic pagination."""
    now = datetime.now(UTC)
    oldest = _insert_account(
        session,
        staff_id="00000000-0000-0000-0000-000000000001",
        login="admin-alpha",
        email="admin.alpha@example.com",
        role="admin",
        is_active=True,
        created_at=now - timedelta(minutes=3),
    )
    hr_enabled = _insert_account(
        session,
        staff_id="00000000-0000-0000-0000-000000000002",
        login="hr-bravo",
        email="hr.bravo@example.com",
        role="hr",
        is_active=True,
        created_at=now - timedelta(minutes=2),
    )
    hr_disabled = _insert_account(
        session,
        staff_id="00000000-0000-0000-0000-000000000003",
        login="hr-charlie",
        email="disabled@example.com",
        role="hr",
        is_active=False,
        created_at=now - timedelta(minutes=1),
    )
    newest = _insert_account(
        session,
        staff_id="00000000-0000-0000-0000-000000000004",
        login="manager-delta",
        email="manager.delta@example.com",
        role="manager",
        is_active=True,
        created_at=now,
    )

    dao = AdminStaffAccountDAO(session=session)

    paged = dao.list_accounts(limit=2, offset=0)
    assert [item.staff_id for item in paged] == [newest.staff_id, hr_disabled.staff_id]
    assert dao.count_accounts() == 4

    by_login = dao.list_accounts(limit=10, offset=0, search="BRAVO")
    assert [item.staff_id for item in by_login] == [hr_enabled.staff_id]

    by_email = dao.list_accounts(limit=10, offset=0, search="disabled@example.com")
    assert [item.staff_id for item in by_email] == [hr_disabled.staff_id]

    filtered = dao.list_accounts(
        limit=10,
        offset=0,
        role="hr",
        is_active=True,
    )
    assert [item.staff_id for item in filtered] == [hr_enabled.staff_id]
    assert dao.count_accounts(role="hr", is_active=True) == 1
    assert dao.count_accounts(role="admin", is_active=True) == 1
    assert oldest.staff_id != newest.staff_id


def test_update_account_fields_mutates_updated_at(session: Session) -> None:
    """Verify mutable fields persist and `updated_at` is advanced after update."""
    dao = AdminStaffAccountDAO(session=session)
    entity = dao.create_account(
        login="staff-user",
        email="staff-user@example.com",
        password_hash="hash",
        role="hr",
        is_active=True,
    )
    before_updated_at = entity.updated_at

    sleep(0.01)
    updated = dao.update_account_fields(entity=entity, role="manager", is_active=False)

    assert updated.role == "manager"
    assert updated.is_active is False
    assert updated.updated_at > before_updated_at


def test_count_active_admins_counts_only_active_admin_rows(session: Session) -> None:
    """Verify active admin counter excludes inactive and non-admin accounts."""
    now = datetime.now(UTC)
    _insert_account(
        session,
        staff_id="00000000-0000-0000-0000-000000000101",
        login="admin-active",
        email="admin-active@example.com",
        role="admin",
        is_active=True,
        created_at=now,
    )
    _insert_account(
        session,
        staff_id="00000000-0000-0000-0000-000000000102",
        login="admin-inactive",
        email="admin-inactive@example.com",
        role="admin",
        is_active=False,
        created_at=now,
    )
    _insert_account(
        session,
        staff_id="00000000-0000-0000-0000-000000000103",
        login="hr-active",
        email="hr-active@example.com",
        role="hr",
        is_active=True,
        created_at=now,
    )

    dao = AdminStaffAccountDAO(session=session)

    assert dao.count_active_admins() == 1
