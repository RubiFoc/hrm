"""Unit tests for audit read service validation and response shaping."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.audit.dao.audit_event_read_dao import AuditEventReadDAO
from hrm_backend.audit.services.audit_read_service import AuditReadService
from hrm_backend.core.models.base import Base


@pytest.fixture()
def session(tmp_path) -> Session:
    """Provide temporary SQLite session for audit read service tests."""
    database_url = f"sqlite+pysqlite:///{tmp_path / 'audit_read_service.db'}"
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db_session:
            yield db_session
    finally:
        engine.dispose()


def test_invalid_time_range_raises_422_without_querying_storage() -> None:
    """Verify occurred_from > occurred_to returns deterministic reason code."""

    class _ExplodingDAO:
        def list_events(self, **_: object):  # noqa: ANN401
            raise AssertionError("DAO list should not be called for invalid time range")

        def count_events(self, **_: object):  # noqa: ANN401
            raise AssertionError("DAO count should not be called for invalid time range")

    service = AuditReadService(dao=_ExplodingDAO())  # type: ignore[arg-type]
    now = datetime.now(UTC)

    with pytest.raises(HTTPException) as exc_info:
        service.list_events(
            limit=20,
            offset=0,
            occurred_from=now + timedelta(seconds=1),
            occurred_to=now,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid_time_range"


def test_empty_result_returns_stable_pagination_fields(session: Session) -> None:
    """Verify empty query result yields a stable response payload."""
    service = AuditReadService(dao=AuditEventReadDAO(session=session))

    response = service.list_events(limit=20, offset=0)

    assert response.items == []
    assert response.total == 0
    assert response.limit == 20
    assert response.offset == 0

