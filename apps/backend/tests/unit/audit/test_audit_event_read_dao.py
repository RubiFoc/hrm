"""Unit tests for audit event read DAO filtering, ordering, and pagination."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.audit.dao.audit_event_read_dao import AuditEventReadDAO
from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.core.models.base import Base


@pytest.fixture()
def session(tmp_path) -> Session:
    """Provide temporary SQLite session for audit read DAO tests."""
    database_url = f"sqlite+pysqlite:///{tmp_path / 'audit_event_read_dao.db'}"
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db_session:
            yield db_session
    finally:
        engine.dispose()


def _insert_event(
    session: Session,
    *,
    event_id: str,
    occurred_at: datetime,
    action: str,
    result: str,
    source: str = "api",
    resource_type: str = "auth",
    correlation_id: str | None = None,
) -> None:
    """Insert deterministic audit event row for assertions."""
    session.add(
        AuditEvent(
            event_id=event_id,
            occurred_at=occurred_at,
            source=source,
            actor_sub="actor-1",
            actor_role="admin",
            action=action,
            resource_type=resource_type,
            resource_id=None,
            result=result,
            reason=None,
            correlation_id=correlation_id,
            ip="127.0.0.1",
            user_agent="pytest",
        )
    )
    session.commit()


def test_list_events_orders_by_occurred_at_desc_then_event_id_desc(session: Session) -> None:
    """Verify DAO ordering is deterministic even when timestamps match."""
    now = datetime.now(UTC)
    _insert_event(
        session,
        event_id="00000000-0000-0000-0000-000000000001",
        occurred_at=now - timedelta(seconds=2),
        action="auth.login",
        result="success",
    )
    _insert_event(
        session,
        event_id="00000000-0000-0000-0000-000000000002",
        occurred_at=now - timedelta(seconds=1),
        action="auth.login",
        result="success",
    )
    _insert_event(
        session,
        event_id="00000000-0000-0000-0000-000000000003",
        occurred_at=now - timedelta(seconds=1),
        action="auth.login",
        result="failure",
    )

    dao = AuditEventReadDAO(session=session)

    page = dao.list_events(limit=2, offset=0)
    assert [event.event_id for event in page] == [
        "00000000-0000-0000-0000-000000000003",
        "00000000-0000-0000-0000-000000000002",
    ]

    tail = dao.list_events(limit=10, offset=2)
    assert [event.event_id for event in tail] == ["00000000-0000-0000-0000-000000000001"]


def test_list_and_count_apply_exact_filters(session: Session) -> None:
    """Verify DAO list/count share the same filter semantics."""
    now = datetime.now(UTC)
    _insert_event(
        session,
        event_id="00000000-0000-0000-0000-000000000101",
        occurred_at=now - timedelta(seconds=3),
        action="auth.login",
        result="success",
        correlation_id="corr-a",
    )
    _insert_event(
        session,
        event_id="00000000-0000-0000-0000-000000000102",
        occurred_at=now - timedelta(seconds=2),
        action="auth.login",
        result="failure",
        correlation_id="corr-a",
    )
    _insert_event(
        session,
        event_id="00000000-0000-0000-0000-000000000103",
        occurred_at=now - timedelta(seconds=1),
        action="admin.staff:list",
        result="success",
        resource_type="staff_account",
        correlation_id="corr-b",
    )

    dao = AuditEventReadDAO(session=session)

    filtered = dao.list_events(
        limit=100,
        offset=0,
        action="auth.login",
        result="success",  # type: ignore[arg-type]
        correlation_id="corr-a",
    )
    assert [event.event_id for event in filtered] == ["00000000-0000-0000-0000-000000000101"]

    total = dao.count_events(
        action="auth.login",
        result="success",  # type: ignore[arg-type]
        correlation_id="corr-a",
    )
    assert total == 1

