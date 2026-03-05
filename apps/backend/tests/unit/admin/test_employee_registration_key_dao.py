"""Unit tests for admin employee registration key DAO list/revoke behavior."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.admin.dao.employee_registration_key_dao import AdminEmployeeRegistrationKeyDAO
from hrm_backend.auth.models.employee_registration_key import EmployeeRegistrationKey
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.core.models.base import Base


@pytest.fixture()
def session(tmp_path) -> Session:
    """Provide temporary SQLite session for employee-key DAO tests."""
    database_url = f"sqlite+pysqlite:///{tmp_path / 'employee_registration_key_dao.db'}"
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db_session:
            yield db_session
    finally:
        engine.dispose()


def _insert_staff(
    session: Session,
    *,
    staff_id: str,
    login: str,
    role: str,
) -> None:
    """Insert deterministic staff account row for FK-safe key rows."""
    now = datetime.now(UTC)
    session.add(
        StaffAccount(
            staff_id=staff_id,
            login=login,
            email=f"{login}@example.com",
            password_hash="hash",
            role=role,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()


def _insert_key(
    session: Session,
    *,
    key_id: str,
    employee_key: str,
    target_role: str,
    expires_at: datetime,
    created_by_staff_id: str,
    created_at: datetime,
    used_at: datetime | None = None,
    revoked_at: datetime | None = None,
    revoked_by_staff_id: str | None = None,
) -> EmployeeRegistrationKey:
    """Insert deterministic employee registration key row for filter assertions."""
    entity = EmployeeRegistrationKey(
        key_id=key_id,
        employee_key=employee_key,
        target_role=target_role,
        expires_at=expires_at,
        used_at=used_at,
        revoked_at=revoked_at,
        revoked_by_staff_id=revoked_by_staff_id,
        created_by_staff_id=created_by_staff_id,
        created_at=created_at,
    )
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return entity


def test_list_and_count_apply_filters_status_and_search(session: Session) -> None:
    """Verify DAO list/count enforce lifecycle filters, pagination, and key search."""
    creator_a = "00000000-0000-0000-0000-0000000000a1"
    creator_b = "00000000-0000-0000-0000-0000000000b1"
    _insert_staff(session, staff_id=creator_a, login="creator-a", role="admin")
    _insert_staff(session, staff_id=creator_b, login="creator-b", role="hr")

    now = datetime.now(UTC)
    active = _insert_key(
        session,
        key_id="00000000-0000-0000-0000-000000000101",
        employee_key="00000000-0000-0000-0000-000000000201",
        target_role="employee",
        expires_at=now + timedelta(days=2),
        created_by_staff_id=creator_a,
        created_at=now - timedelta(minutes=4),
    )
    used = _insert_key(
        session,
        key_id="00000000-0000-0000-0000-000000000102",
        employee_key="00000000-0000-0000-0000-000000000202",
        target_role="manager",
        expires_at=now + timedelta(days=1),
        created_by_staff_id=creator_a,
        created_at=now - timedelta(minutes=3),
        used_at=now - timedelta(minutes=1),
    )
    expired = _insert_key(
        session,
        key_id="00000000-0000-0000-0000-000000000103",
        employee_key="00000000-0000-0000-0000-000000000203",
        target_role="employee",
        expires_at=now - timedelta(minutes=5),
        created_by_staff_id=creator_b,
        created_at=now - timedelta(minutes=2),
    )
    revoked = _insert_key(
        session,
        key_id="00000000-0000-0000-0000-000000000104",
        employee_key="00000000-0000-0000-0000-000000000204",
        target_role="leader",
        expires_at=now + timedelta(days=3),
        created_by_staff_id=creator_b,
        created_at=now - timedelta(minutes=1),
        revoked_at=now,
        revoked_by_staff_id=creator_b,
    )

    dao = AdminEmployeeRegistrationKeyDAO(session=session)

    page = dao.list_keys(limit=2, offset=0)
    assert [item.key_id for item in page] == [revoked.key_id, expired.key_id]
    assert dao.count_keys() == 4

    active_rows = dao.list_keys(limit=10, offset=0, status="active")
    assert [item.key_id for item in active_rows] == [active.key_id]

    used_rows = dao.list_keys(limit=10, offset=0, status="used")
    assert [item.key_id for item in used_rows] == [used.key_id]

    expired_rows = dao.list_keys(limit=10, offset=0, status="expired")
    assert [item.key_id for item in expired_rows] == [expired.key_id]

    revoked_rows = dao.list_keys(limit=10, offset=0, status="revoked")
    assert [item.key_id for item in revoked_rows] == [revoked.key_id]

    by_creator = dao.list_keys(limit=10, offset=0, created_by_staff_id=creator_b)
    assert [item.key_id for item in by_creator] == [revoked.key_id, expired.key_id]

    by_search = dao.list_keys(limit=10, offset=0, search="000000000202")
    assert [item.key_id for item in by_search] == [used.key_id]

    by_role = dao.list_keys(limit=10, offset=0, target_role="manager")
    assert [item.key_id for item in by_role] == [used.key_id]


def test_revoke_key_persists_revocation_fields(session: Session) -> None:
    """Verify DAO revoke mutation stores revocation timestamp and actor id."""
    creator = "00000000-0000-0000-0000-0000000000c1"
    revoker = "00000000-0000-0000-0000-0000000000c2"
    _insert_staff(session, staff_id=creator, login="creator-c", role="admin")
    _insert_staff(session, staff_id=revoker, login="revoker-c", role="hr")

    now = datetime.now(UTC)
    entity = _insert_key(
        session,
        key_id="00000000-0000-0000-0000-000000000301",
        employee_key="00000000-0000-0000-0000-000000000401",
        target_role="employee",
        expires_at=now + timedelta(days=1),
        created_by_staff_id=creator,
        created_at=now,
    )

    dao = AdminEmployeeRegistrationKeyDAO(session=session)
    revoked = dao.revoke_key(
        entity=entity,
        revoked_at=now,
        revoked_by_staff_id=revoker,
    )

    assert revoked.revoked_at is not None
    assert revoked.revoked_by_staff_id == revoker
