"""Unit tests for auth employee registration key DAO consume semantics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.auth.infra.postgres.employee_registration_key_dao import EmployeeRegistrationKeyDAO
from hrm_backend.auth.models.employee_registration_key import EmployeeRegistrationKey
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.core.models.base import Base


@pytest.fixture()
def session(tmp_path) -> Session:
    """Provide SQLite session for registration key DAO tests."""
    database_url = f"sqlite+pysqlite:///{tmp_path / 'auth_registration_key_dao.db'}"
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db_session:
            yield db_session
    finally:
        engine.dispose()


def _insert_staff(session: Session, staff_id: str) -> None:
    """Insert one staff account row for key foreign-key linkage."""
    now = datetime.now(UTC)
    session.add(
        StaffAccount(
            staff_id=staff_id,
            login="issuer",
            email="issuer@example.com",
            password_hash="hash",
            role="admin",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()


def _insert_key(
    session: Session,
    *,
    employee_key: str,
    target_role: str,
    created_by_staff_id: str,
    expires_at: datetime,
    used_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> None:
    """Insert one key row with deterministic timestamp fields."""
    session.add(
        EmployeeRegistrationKey(
            employee_key=employee_key,
            target_role=target_role,
            expires_at=expires_at,
            used_at=used_at,
            revoked_at=revoked_at,
            created_by_staff_id=created_by_staff_id,
        )
    )
    session.commit()


def test_consume_key_rejects_revoked_key(session: Session) -> None:
    """Verify revoked key cannot be consumed by registration flow."""
    staff_id = "00000000-0000-0000-0000-0000000000d1"
    _insert_staff(session, staff_id)
    key_value = "00000000-0000-0000-0000-000000000501"
    _insert_key(
        session,
        employee_key=key_value,
        target_role="employee",
        created_by_staff_id=staff_id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        revoked_at=datetime.now(UTC),
    )

    dao = EmployeeRegistrationKeyDAO(session=session)
    consumed = dao.consume_key(employee_key=key_value, target_role="employee")

    assert consumed is None


def test_consume_key_marks_used_at_for_valid_active_key(session: Session) -> None:
    """Verify valid active key is consumed once and receives `used_at` timestamp."""
    staff_id = "00000000-0000-0000-0000-0000000000d2"
    _insert_staff(session, staff_id)
    key_value = "00000000-0000-0000-0000-000000000502"
    _insert_key(
        session,
        employee_key=key_value,
        target_role="employee",
        created_by_staff_id=staff_id,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )

    dao = EmployeeRegistrationKeyDAO(session=session)
    consumed = dao.consume_key(employee_key=key_value, target_role="employee")

    assert consumed is not None
    assert consumed.used_at is not None
