"""Integration tests for audit recording across API and background policy paths."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.audit.dao.audit_event_dao import AuditEventDAO
from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.rbac import BackgroundAccessDeniedError, enforce_background_permission
from hrm_backend.settings import AppSettings, get_settings


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'audit_enforcement.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure application dependency overrides for SQLite-backed audit tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
    )
    context_holder = {
        "context": AuthContext(
            subject_id="hr-user",
            role="hr",
            session_id="sid-1",
            token_id="jti-1",
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


def test_api_permission_decisions_are_audited(configured_app) -> None:
    """Verify allowed/denied API permission checks persist audit events."""
    configured, context_holder, database_url = configured_app

    with TestClient(configured) as client:
        context_holder["context"] = AuthContext(
            subject_id="hr-actor",
            role="hr",
            session_id="sid-hr",
            token_id="jti-hr",
            expires_at=9999999999,
        )
        allow_response = client.post("/api/v1/vacancies", headers={"X-Request-ID": "req-allow-1"})
        assert allow_response.status_code == 200
        assert allow_response.headers.get("X-Request-ID") == "req-allow-1"

        context_holder["context"] = AuthContext(
            subject_id="candidate-actor",
            role="candidate",
            session_id="sid-cand",
            token_id="jti-cand",
            expires_at=9999999999,
        )
        deny_response = client.post("/api/v1/vacancies", headers={"X-Request-ID": "req-deny-1"})
        assert deny_response.status_code == 403
        assert deny_response.headers.get("X-Request-ID") == "req-deny-1"

        context_holder["context"] = AuthContext(
            subject_id="unknown-role-actor",
            role="intern",
            session_id="sid-unknown",
            token_id="jti-unknown",
            expires_at=9999999999,
        )
        unknown_role_response = client.post(
            "/api/v1/vacancies",
            headers={"X-Request-ID": "req-unknown-role-1"},
        )
        assert unknown_role_response.status_code == 403
        assert unknown_role_response.headers.get("X-Request-ID") == "req-unknown-role-1"

    events = _load_events(database_url)
    permission_events = [event for event in events if event.action == "vacancy:create"]
    assert len(permission_events) == 3
    assert permission_events[0].result == "allowed"
    assert permission_events[0].actor_sub == "hr-actor"
    assert permission_events[0].correlation_id == "req-allow-1"
    assert permission_events[1].result == "denied"
    assert permission_events[1].actor_sub == "candidate-actor"
    assert permission_events[1].correlation_id == "req-deny-1"
    assert permission_events[2].result == "denied"
    assert permission_events[2].actor_sub == "unknown-role-actor"
    assert permission_events[2].reason == "Unknown role claim: intern"
    assert permission_events[2].correlation_id == "req-unknown-role-1"


def test_auth_login_is_audited(configured_app) -> None:
    """Verify auth login endpoint records successful audit event."""
    configured, _, database_url = configured_app

    with TestClient(configured) as client:
        response = client.post(
            "/api/v1/auth/login",
            headers={"X-Request-ID": "req-login-1"},
            json={"subject_id": "login-user-1", "role": "hr"},
        )
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == "req-login-1"

    events = _load_events(database_url)
    login_events = [event for event in events if event.action == "auth.login"]
    assert len(login_events) == 1
    assert login_events[0].result == "success"
    assert login_events[0].actor_sub == "login-user-1"
    assert login_events[0].actor_role == "hr"
    assert login_events[0].correlation_id == "req-login-1"


def test_background_enforcement_writes_job_audit_event(sqlite_database_url: str) -> None:
    """Verify denied background permission writes job-sourced audit event."""
    engine = create_engine(sqlite_database_url, future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            service = AuditService(dao=AuditEventDAO(session=session))
            with pytest.raises(BackgroundAccessDeniedError):
                enforce_background_permission(
                    subject_id="job-user-1",
                    role="candidate",
                    permission="vacancy:create",
                    audit_service=service,
                    correlation_id="job-req-1",
                )
        events = _load_events(sqlite_database_url)
        job_events = [event for event in events if event.source == "job"]
        assert len(job_events) == 1
        assert job_events[0].result == "denied"
        assert job_events[0].correlation_id == "job-req-1"
        assert job_events[0].actor_sub == "job-user-1"
    finally:
        engine.dispose()
