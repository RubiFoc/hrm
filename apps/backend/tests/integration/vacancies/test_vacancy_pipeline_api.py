"""Integration tests for vacancy CRUD and pipeline transition APIs."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'vacancy_pipeline.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for vacancy pipeline tests."""
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
    with Session(engine) as session:
        session.add(
            CandidateProfile(
                candidate_id="cand-1",
                owner_subject_id="candidate-1",
                first_name="A",
                last_name="B",
                email="candidate-1@example.com",
                phone=None,
                location=None,
                current_title=None,
                extra_data={},
            )
        )
        session.add(
            CandidateProfile(
                candidate_id="cand-2",
                owner_subject_id="candidate-2",
                first_name="C",
                last_name="D",
                email="candidate-2@example.com",
                phone=None,
                location=None,
                current_title=None,
                extra_data={},
            )
        )
        session.commit()

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


def test_vacancy_crud_and_pipeline_transitions(configured_app) -> None:
    """Verify vacancy CRUD and canonical pipeline transitions."""
    configured, _, _ = configured_app

    with TestClient(configured) as client:
        create_response = client.post(
            "/api/v1/vacancies",
            json={
                "title": "ML Engineer",
                "description": "Build matching services",
                "department": "Engineering",
                "status": "open",
            },
        )
        assert create_response.status_code == 200
        vacancy_id = create_response.json()["vacancy_id"]

        list_response = client.get("/api/v1/vacancies")
        assert list_response.status_code == 200
        assert len(list_response.json()["items"]) == 1

        get_response = client.get(f"/api/v1/vacancies/{vacancy_id}")
        assert get_response.status_code == 200

        patch_response = client.patch(
            f"/api/v1/vacancies/{vacancy_id}",
            json={"status": "active"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["status"] == "active"

        stages = [
            "applied",
            "screening",
            "shortlist",
            "interview",
            "offer",
            "hired",
        ]
        for stage in stages:
            transition = client.post(
                "/api/v1/pipeline/transitions",
                json={
                    "vacancy_id": vacancy_id,
                    "candidate_id": "cand-1",
                    "to_stage": stage,
                    "reason": "progress",
                },
            )
            assert transition.status_code == 200

        invalid_transition = client.post(
            "/api/v1/pipeline/transitions",
            json={
                "vacancy_id": vacancy_id,
                "candidate_id": "cand-2",
                "to_stage": "offer",
                "reason": "skip",
            },
        )
        assert invalid_transition.status_code == 422
        assert "not allowed" in invalid_transition.json()["detail"]


def test_pipeline_transition_rbac_deny_is_audited(configured_app) -> None:
    """Verify pipeline transition deny path records RBAC audit event."""
    configured, context_holder, database_url = configured_app

    with TestClient(configured) as client:
        create_response = client.post(
            "/api/v1/vacancies",
            json={
                "title": "Data Engineer",
                "description": "Build ETL",
                "department": "Data",
                "status": "open",
            },
        )
        vacancy_id = create_response.json()["vacancy_id"]

        context_holder["context"] = AuthContext(
            subject_id=uuid4(),
            role="manager",
            session_id=uuid4(),
            token_id=uuid4(),
            expires_at=9999999999,
        )
        denied_response = client.post(
            "/api/v1/pipeline/transitions",
            json={
                "vacancy_id": vacancy_id,
                "candidate_id": "cand-1",
                "to_stage": "applied",
                "reason": "self-move",
            },
        )
        assert denied_response.status_code == 403

    events = _load_events(database_url)
    denied_events = [
        event
        for event in events
        if event.action == "pipeline:transition" and event.result == "denied"
    ]
    assert len(denied_events) >= 1
    assert denied_events[-1].actor_role == "manager"
