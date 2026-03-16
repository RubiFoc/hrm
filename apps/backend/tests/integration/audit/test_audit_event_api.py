"""Integration tests for admin audit event query API and audit hooks."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for audit query integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'audit_event_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure application dependency overrides for SQLite-backed audit query tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
    )
    context_holder = {
        "context": AuthContext(
            subject_id=uuid4(),
            role="admin",
            session_id=uuid4(),
            token_id=uuid4(),
            expires_at=9999999999,
        )
    }

    def _get_settings_override() -> AppSettings:
        return settings

    def _get_auth_context_override() -> AuthContext:
        return context_holder["context"]

    app.dependency_overrides[get_settings] = _get_settings_override
    app.dependency_overrides[get_current_auth_context] = _get_auth_context_override

    engine = create_engine(sqlite_database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        yield app, context_holder, sqlite_database_url
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide in-process async API client for audit query integration tests."""
    configured, _, _ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


def _insert_event(
    database_url: str,
    *,
    event_id: str,
    occurred_at: datetime,
    action: str,
    result: str,
    correlation_id: str,
) -> None:
    """Insert deterministic audit event row for API list assertions."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                AuditEvent(
                    event_id=event_id,
                    occurred_at=occurred_at,
                    source="api",
                    actor_sub="actor-1",
                    actor_role="admin",
                    action=action,
                    resource_type="auth",
                    resource_id=None,
                    result=result,
                    reason="reason-1" if result == "failure" else None,
                    correlation_id=correlation_id,
                    ip="127.0.0.1",
                    user_agent="pytest",
                )
            )
            session.commit()
    finally:
        engine.dispose()


def _load_events(database_url: str) -> list[AuditEvent]:
    """Load ordered audit events from database URL."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            return list(
                session.execute(
                    select(AuditEvent).order_by(AuditEvent.occurred_at, AuditEvent.event_id)
                ).scalars()
            )
    finally:
        engine.dispose()


async def test_admin_can_list_audit_events_with_combined_filters(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify admin list endpoint applies exact filters and stable ordering."""
    _, context_holder, database_url = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    now = datetime.now(UTC)
    _insert_event(
        database_url,
        event_id="00000000-0000-0000-0000-000000000201",
        occurred_at=now - timedelta(seconds=3),
        action="auth.login",
        result="success",
        correlation_id="corr-1",
    )
    _insert_event(
        database_url,
        event_id="00000000-0000-0000-0000-000000000202",
        occurred_at=now - timedelta(seconds=2),
        action="auth.login",
        result="success",
        correlation_id="corr-1",
    )
    _insert_event(
        database_url,
        event_id="00000000-0000-0000-0000-000000000203",
        occurred_at=now - timedelta(seconds=1),
        action="auth.login",
        result="failure",
        correlation_id="corr-1",
    )

    response = await api_client.get(
        "/api/v1/audit/events",
        params={
            "limit": 100,
            "offset": 0,
            "action": "auth.login",
            "correlation_id": "corr-1",
            "result": "success",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert [item["event_id"] for item in payload["items"]] == [
        "00000000-0000-0000-0000-000000000202",
        "00000000-0000-0000-0000-000000000201",
    ]
    assert all(item["ip"] == "127.0.0.1" for item in payload["items"])
    assert all(item["user_agent"] == "pytest" for item in payload["items"])


async def test_non_admin_gets_403_for_audit_events_list(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify non-admin roles are denied for audit evidence query API."""
    _, context_holder, _ = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="hr",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    response = await api_client.get("/api/v1/audit/events")

    assert response.status_code == 403


async def test_invalid_time_range_returns_422_and_is_audited(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify invalid time range returns deterministic reason code and is audited."""
    _, context_holder, database_url = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    now = datetime.now(UTC)
    response = await api_client.get(
        "/api/v1/audit/events",
        params={
            "occurred_from": (now + timedelta(seconds=1)).isoformat(),
            "occurred_to": now.isoformat(),
        },
        headers={"X-Request-ID": "req-invalid-time-1"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "invalid_time_range"

    events = _load_events(database_url)
    list_events = [event for event in events if event.action == "audit.event:list"]
    assert any(
        event.result == "failure" and event.reason == "invalid_time_range"
        for event in list_events
    )


async def test_response_excludes_self_generated_audit_event_list(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify endpoint writes audit.event:list after building response."""
    _, context_holder, database_url = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    request_id = "req-audit-self-1"

    response = await api_client.get(
        "/api/v1/audit/events",
        params={"correlation_id": request_id},
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["action"] == "audit:read"
    assert not any(item["action"] == "audit.event:list" for item in payload["items"])

    events = _load_events(database_url)
    assert any(
        event.action == "audit.event:list"
        and event.result == "success"
        and event.correlation_id == request_id
        for event in events
    )


async def test_admin_can_export_audit_events_as_csv_with_combined_filters(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify admin audit export supports filters and returns CSV attachment headers."""
    _, context_holder, database_url = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    now = datetime.now(UTC)
    _insert_event(
        database_url,
        event_id="00000000-0000-0000-0000-000000000201",
        occurred_at=now - timedelta(seconds=3),
        action="auth.login",
        result="success",
        correlation_id="corr-1",
    )
    _insert_event(
        database_url,
        event_id="00000000-0000-0000-0000-000000000202",
        occurred_at=now - timedelta(seconds=2),
        action="auth.login",
        result="success",
        correlation_id="corr-1",
    )
    _insert_event(
        database_url,
        event_id="00000000-0000-0000-0000-000000000203",
        occurred_at=now - timedelta(seconds=1),
        action="auth.login",
        result="failure",
        correlation_id="corr-1",
    )

    response = await api_client.get(
        "/api/v1/audit/events/export",
        params={
            "format": "csv",
            "limit": 100,
            "offset": 0,
            "action": "auth.login",
            "correlation_id": "corr-1",
            "result": "success",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"].startswith('attachment; filename="audit-events-')
    assert response.headers["content-disposition"].endswith('.csv"')

    rows = list(csv.reader(StringIO(response.text)))
    header = rows[0]
    event_id_index = header.index("event_id")
    assert [row[event_id_index] for row in rows[1:]] == [
        "00000000-0000-0000-0000-000000000202",
        "00000000-0000-0000-0000-000000000201",
    ]

    events = _load_events(database_url)
    assert any(
        event.action == "audit.event:export"
        and event.result == "success"
        and event.reason == "csv"
        for event in events
    )


async def test_admin_can_export_audit_events_as_jsonl(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify export supports JSONL output and returns parseable NDJSON payload."""
    _, context_holder, database_url = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    now = datetime.now(UTC)
    _insert_event(
        database_url,
        event_id="00000000-0000-0000-0000-000000000301",
        occurred_at=now - timedelta(seconds=1),
        action="auth.me",
        result="success",
        correlation_id="corr-jsonl-1",
    )

    response = await api_client.get(
        "/api/v1/audit/events/export",
        params={
            "format": "jsonl",
            "limit": 10,
            "offset": 0,
            "action": "auth.me",
            "correlation_id": "corr-jsonl-1",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert response.headers["content-disposition"].endswith('.jsonl"')

    lines = response.text.strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["event_id"] == "00000000-0000-0000-0000-000000000301"


async def test_non_admin_gets_403_for_audit_events_export(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify non-admin roles are denied for audit export API."""
    _, context_holder, _ = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="hr",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    response = await api_client.get(
        "/api/v1/audit/events/export",
        params={"format": "csv"},
    )

    assert response.status_code == 403


async def test_export_response_excludes_self_generated_audit_event_export(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify export endpoint writes audit.event:export after building attachment content."""
    _, context_holder, database_url = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    request_id = "req-audit-export-self-1"

    response = await api_client.get(
        "/api/v1/audit/events/export",
        params={"format": "csv", "correlation_id": request_id, "limit": 100, "offset": 0},
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    rows = list(csv.reader(StringIO(response.text)))
    header = rows[0]
    action_index = header.index("action")
    assert len(rows) == 2
    assert rows[1][action_index] == "audit:read"
    assert not any(row[action_index] == "audit.event:export" for row in rows[1:])

    events = _load_events(database_url)
    assert any(
        event.action == "audit.event:export"
        and event.result == "success"
        and event.correlation_id == request_id
        for event in events
    )
