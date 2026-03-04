"""Integration tests for candidate CRUD and CV upload/download APIs."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dependencies.candidates import get_candidate_storage
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings


class InMemoryCandidateStorage:
    """In-memory object storage replacement for integration tests."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def put_object(
        self,
        *,
        object_key: str,
        data: bytes,
        mime_type: str,
        enable_sse: bool,
    ) -> None:
        del mime_type, enable_sse
        self._store[object_key] = data

    def get_object(self, *, object_key: str) -> bytes:
        return self._store[object_key]


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'candidate_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure application dependency overrides for candidate integration tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
        cv_max_size_bytes=32,
    )
    storage = InMemoryCandidateStorage()
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

    def _get_storage_override() -> InMemoryCandidateStorage:
        return storage

    app.dependency_overrides[get_settings] = _get_settings_override
    app.dependency_overrides[get_current_auth_context] = _get_auth_context_override
    app.dependency_overrides[get_candidate_storage] = _get_storage_override

    engine = create_engine(sqlite_database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        yield app, context_holder, storage, sqlite_database_url
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_candidate_storage, None)
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


def test_candidate_crud_and_ownership_deny_are_enforced(configured_app) -> None:
    """Verify candidate CRUD with RBAC deny trace for non-privileged staff role."""
    configured, context_holder, _, database_url = configured_app

    with TestClient(configured) as client:
        create_response = client.post(
            "/api/v1/candidates",
            json={
                "owner_subject_id": "another-owner",
                "first_name": "Alice",
                "last_name": "Doe",
                "email": "Alice@example.com",
                "phone": "+375291112233",
                "location": "Minsk",
                "current_title": "Backend Engineer",
                "extra_data": {"stack": "python"},
            },
        )
        assert create_response.status_code == 200
        payload = create_response.json()
        candidate_id = payload["candidate_id"]
        assert payload["owner_subject_id"] == "another-owner"
        assert payload["email"] == "alice@example.com"

        get_response = client.get(f"/api/v1/candidates/{candidate_id}")
        assert get_response.status_code == 200

        patch_response = client.patch(
            f"/api/v1/candidates/{candidate_id}",
            json={"current_title": "Senior Backend Engineer"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["current_title"] == "Senior Backend Engineer"

        context_holder["context"] = AuthContext(
            subject_id=uuid4(),
            role="manager",
            session_id=uuid4(),
            token_id=uuid4(),
            expires_at=9999999999,
        )
        forbidden_get = client.get(f"/api/v1/candidates/{candidate_id}")
        assert forbidden_get.status_code == 403

        forbidden_list = client.get("/api/v1/candidates")
        assert forbidden_list.status_code == 403

        context_holder["context"] = AuthContext(
            subject_id=uuid4(),
            role="hr",
            session_id=uuid4(),
            token_id=uuid4(),
            expires_at=9999999999,
        )
        list_response = client.get("/api/v1/candidates")
        assert list_response.status_code == 200
        assert len(list_response.json()["items"]) == 1

    events = _load_events(database_url)
    permission_denials = [
        event
        for event in events
        if event.action == "candidate_profile:read" and event.result == "denied"
    ]
    assert len(permission_denials) == 1
    assert permission_denials[0].actor_role == "manager"
    assert "has no permission" in (permission_denials[0].reason or "")


def test_cv_upload_download_status_and_validation_failures(configured_app) -> None:
    """Verify CV upload/download/status and validation error contracts."""
    configured, context_holder, _, _ = configured_app

    with TestClient(configured) as client:
        create_response = client.post(
            "/api/v1/candidates",
            json={
                "first_name": "Bob",
                "last_name": "Miller",
                "email": "bob@example.com",
                "extra_data": {},
            },
        )
        candidate_id = create_response.json()["candidate_id"]

        valid_content = b"pdf-content"
        valid_checksum = hashlib.sha256(valid_content).hexdigest()
        upload_response = client.post(
            f"/api/v1/candidates/{candidate_id}/cv",
            data={"checksum_sha256": valid_checksum},
            files={"file": ("cv.pdf", valid_content, "application/pdf")},
        )
        assert upload_response.status_code == 200
        upload_payload = upload_response.json()
        assert upload_payload["size_bytes"] == len(valid_content)

        download_response = client.get(f"/api/v1/candidates/{candidate_id}/cv")
        assert download_response.status_code == 200
        assert download_response.content == valid_content
        assert "attachment; filename=\"cv.pdf\"" in download_response.headers["content-disposition"]

        status_response = client.get(f"/api/v1/candidates/{candidate_id}/cv/parsing-status")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "queued"

        bad_mime_content = b"plain-text"
        bad_mime_checksum = hashlib.sha256(bad_mime_content).hexdigest()
        bad_mime_response = client.post(
            f"/api/v1/candidates/{candidate_id}/cv",
            data={"checksum_sha256": bad_mime_checksum},
            files={"file": ("cv.txt", bad_mime_content, "text/plain")},
        )
        assert bad_mime_response.status_code == 415

        bad_checksum_response = client.post(
            f"/api/v1/candidates/{candidate_id}/cv",
            data={"checksum_sha256": "0" * 64},
            files={"file": ("cv.pdf", valid_content, "application/pdf")},
        )
        assert bad_checksum_response.status_code == 422

        oversized_content = b"x" * 33
        oversized_checksum = hashlib.sha256(oversized_content).hexdigest()
        oversized_response = client.post(
            f"/api/v1/candidates/{candidate_id}/cv",
            data={"checksum_sha256": oversized_checksum},
            files={"file": ("cv.pdf", oversized_content, "application/pdf")},
        )
        assert oversized_response.status_code == 413

        context_holder["context"] = AuthContext(
            subject_id=uuid4(),
            role="manager",
            session_id=uuid4(),
            token_id=uuid4(),
            expires_at=9999999999,
        )
        denied_status = client.get(f"/api/v1/candidates/{candidate_id}/cv/parsing-status")
        assert denied_status.status_code == 403
