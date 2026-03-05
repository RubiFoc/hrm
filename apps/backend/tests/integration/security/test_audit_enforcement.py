"""Integration tests for audit recording across API and background policy paths."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

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
            subject_id=uuid4(),
            role="hr",
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
            subject_id=uuid4(),
            role="hr",
            session_id=uuid4(),
            token_id=uuid4(),
            expires_at=9999999999,
        )
        allow_response = client.post(
            "/api/v1/vacancies",
            headers={"X-Request-ID": "req-allow-1"},
            json={
                "title": "Backend Engineer",
                "description": "Build recruitment platform modules",
                "department": "Engineering",
                "status": "open",
            },
        )
        assert allow_response.status_code == 200
        assert allow_response.headers.get("X-Request-ID") == "req-allow-1"

        context_holder["context"] = AuthContext(
            subject_id=uuid4(),
            role="manager",
            session_id=uuid4(),
            token_id=uuid4(),
            expires_at=9999999999,
        )
        deny_response = client.post(
            "/api/v1/vacancies",
            headers={"X-Request-ID": "req-deny-1"},
            json={
                "title": "Backend Engineer",
                "description": "Build recruitment platform modules",
                "department": "Engineering",
                "status": "open",
            },
        )
        assert deny_response.status_code == 403
        assert deny_response.headers.get("X-Request-ID") == "req-deny-1"

        context_holder["context"] = AuthContext(
            subject_id=uuid4(),
            role="intern",
            session_id=uuid4(),
            token_id=uuid4(),
            expires_at=9999999999,
        )
        unknown_role_response = client.post(
            "/api/v1/vacancies",
            headers={"X-Request-ID": "req-unknown-role-1"},
            json={
                "title": "Backend Engineer",
                "description": "Build recruitment platform modules",
                "department": "Engineering",
                "status": "open",
            },
        )
        assert unknown_role_response.status_code == 403
        assert unknown_role_response.headers.get("X-Request-ID") == "req-unknown-role-1"

    events = _load_events(database_url)
    permission_events = [
        event
        for event in events
        if event.action == "vacancy:create" and event.result in {"allowed", "denied"}
    ]
    assert len(permission_events) == 3
    assert permission_events[0].result == "allowed"
    assert permission_events[0].actor_sub is not None
    assert permission_events[0].correlation_id == "req-allow-1"
    assert permission_events[1].result == "denied"
    assert permission_events[1].actor_sub is not None
    assert permission_events[1].correlation_id == "req-deny-1"
    assert permission_events[2].result == "denied"
    assert permission_events[2].actor_sub is not None
    assert permission_events[2].reason == "Unknown role claim: intern"
    assert permission_events[2].correlation_id == "req-unknown-role-1"


def test_auth_login_is_audited(configured_app) -> None:
    """Verify auth login endpoint records successful audit event."""
    configured, context_holder, database_url = configured_app

    login_identifier = f"hr-{uuid4().hex[:8]}"
    login_password = "IntegrationPassword!123"
    login_email = f"{login_identifier}@example.com"
    with TestClient(configured) as client:
        context_holder["context"] = AuthContext(
            subject_id=uuid4(),
            role="admin",
            session_id=uuid4(),
            token_id=uuid4(),
            expires_at=9999999999,
        )
        create_response = client.post(
            "/api/v1/admin/staff",
            headers={"X-Request-ID": "req-create-staff-1"},
            json={
                "login": login_identifier,
                "email": login_email,
                "password": login_password,
                "role": "hr",
                "is_active": True,
            },
        )
        assert create_response.status_code == 200
        created_staff_id = create_response.json()["staff_id"]

        response = client.post(
            "/api/v1/auth/login",
            headers={"X-Request-ID": "req-login-1"},
            json={"identifier": login_identifier, "password": login_password},
        )
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == "req-login-1"

    events = _load_events(database_url)
    login_events = [event for event in events if event.action == "auth.login"]
    assert len(login_events) == 1
    assert login_events[0].result == "success"
    assert created_staff_id  # ensure staff creation succeeded with persisted identifier
    assert login_events[0].actor_sub == login_identifier
    assert login_events[0].actor_role is None
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
