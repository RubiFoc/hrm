"""Integration tests for async CV parsing worker and status tracking."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.audit.dao.audit_event_dao import AuditEventDAO
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.cv_parsing_job_dao import CVParsingJobDAO
from hrm_backend.candidates.dependencies.candidates import get_candidate_storage
from hrm_backend.candidates.services.cv_parsing_worker_service import CVParsingWorkerService
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


class InMemoryCandidateStorage:
    """In-memory object storage replacement for parsing integration tests."""

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
    return f"sqlite+pysqlite:///{tmp_path / 'cv_parsing_jobs.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure application dependency overrides for CV parsing integration tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
        cv_max_size_bytes=1024,
        cv_parsing_max_attempts=2,
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
        yield app, settings, context_holder, storage, sqlite_database_url
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_candidate_storage, None)
        engine.dispose()


def _run_worker_once(
    database_url: str,
    settings: AppSettings,
    storage: InMemoryCandidateStorage,
) -> str:
    """Run one worker iteration and return status."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            worker = CVParsingWorkerService(
                settings=settings,
                parsing_job_dao=CVParsingJobDAO(session=session),
                document_dao=CandidateDocumentDAO(session=session),
                storage=storage,  # type: ignore[arg-type]
                audit_service=AuditService(dao=AuditEventDAO(session=session)),
            )
            return worker.process_next_job().status
    finally:
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for parsing integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_parsing_job_success_and_status_tracking(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify queued job moves to succeeded state after worker iteration."""
    _, settings, _, storage, database_url = configured_app

    candidate_response = await api_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Nina",
            "last_name": "Stone",
            "email": "nina@example.com",
            "extra_data": {},
        },
    )
    candidate_id = candidate_response.json()["candidate_id"]

    content = b"normal-parse-content"
    checksum = hashlib.sha256(content).hexdigest()
    upload_response = await api_client.post(
        f"/api/v1/candidates/{candidate_id}/cv",
        data={"checksum_sha256": checksum},
        files={"file": ("cv.pdf", content, "application/pdf")},
    )
    assert upload_response.status_code == 200

    pre_status = await api_client.get(f"/api/v1/candidates/{candidate_id}/cv/parsing-status")
    assert pre_status.status_code == 200
    pre_payload = pre_status.json()
    assert pre_payload["status"] == "queued"
    assert pre_payload["analysis_ready"] is False
    assert pre_payload["detected_language"] == "unknown"

    first_worker_result = _run_worker_once(database_url, settings, storage)
    assert first_worker_result == "succeeded"

    post_status = await api_client.get(f"/api/v1/candidates/{candidate_id}/cv/parsing-status")
    assert post_status.status_code == 200
    post_payload = post_status.json()
    assert post_payload["status"] == "succeeded"
    assert post_payload["analysis_ready"] is True
    assert post_payload["detected_language"] == "en"

    analysis_response = await api_client.get(f"/api/v1/candidates/{candidate_id}/cv/analysis")
    assert analysis_response.status_code == 200
    analysis_payload = analysis_response.json()
    assert analysis_payload["detected_language"] == "en"
    assert analysis_payload["parsed_profile"]["document"]["mime_type"] == "application/pdf"
    assert isinstance(analysis_payload["evidence"], list)
    assert analysis_payload["evidence"]


async def test_public_tracking_endpoints_follow_job_lifecycle(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify anonymous tracking endpoints expose status and analysis by parsing job id."""
    _, settings, _, storage, database_url = configured_app

    candidate_response = await api_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Ira",
            "last_name": "Lane",
            "email": "ira@example.com",
            "extra_data": {},
        },
    )
    candidate_id = candidate_response.json()["candidate_id"]

    content = b"public-tracking-success"
    checksum = hashlib.sha256(content).hexdigest()
    upload_response = await api_client.post(
        f"/api/v1/candidates/{candidate_id}/cv",
        data={"checksum_sha256": checksum},
        files={"file": ("cv.pdf", content, "application/pdf")},
    )
    assert upload_response.status_code == 200

    staff_status_response = await api_client.get(
        f"/api/v1/candidates/{candidate_id}/cv/parsing-status"
    )
    assert staff_status_response.status_code == 200
    job_id = staff_status_response.json()["job_id"]

    public_status_response = await api_client.get(f"/api/v1/public/cv-parsing-jobs/{job_id}")
    assert public_status_response.status_code == 200
    assert public_status_response.json()["status"] == "queued"

    public_analysis_before_ready = await api_client.get(
        f"/api/v1/public/cv-parsing-jobs/{job_id}/analysis"
    )
    assert public_analysis_before_ready.status_code == 409

    worker_result = _run_worker_once(database_url, settings, storage)
    assert worker_result == "succeeded"

    public_status_after_worker = await api_client.get(f"/api/v1/public/cv-parsing-jobs/{job_id}")
    assert public_status_after_worker.status_code == 200
    assert public_status_after_worker.json()["status"] == "succeeded"
    assert public_status_after_worker.json()["analysis_ready"] is True

    public_analysis_response = await api_client.get(
        f"/api/v1/public/cv-parsing-jobs/{job_id}/analysis"
    )
    assert public_analysis_response.status_code == 200
    assert public_analysis_response.json()["candidate_id"] == candidate_id


async def test_parsing_job_failure_path_and_retry_limit(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify failure path retries up to configured limit and then stops."""
    _, settings, _, storage, database_url = configured_app

    candidate_response = await api_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Tom",
            "last_name": "Green",
            "email": "tom@example.com",
            "extra_data": {},
        },
    )
    candidate_id = candidate_response.json()["candidate_id"]

    content = b"FAIL_PARSE deterministic-failure"
    checksum = hashlib.sha256(content).hexdigest()
    upload_response = await api_client.post(
        f"/api/v1/candidates/{candidate_id}/cv",
        data={"checksum_sha256": checksum},
        files={"file": ("cv.pdf", content, "application/pdf")},
    )
    assert upload_response.status_code == 200

    first_worker_result = _run_worker_once(database_url, settings, storage)
    second_worker_result = _run_worker_once(database_url, settings, storage)
    third_worker_result = _run_worker_once(database_url, settings, storage)

    assert first_worker_result == "failed"
    assert second_worker_result == "failed"
    assert third_worker_result == "idle"

    status_response = await api_client.get(f"/api/v1/candidates/{candidate_id}/cv/parsing-status")
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["status"] == "failed"
    assert payload["attempt_count"] == 2
    assert payload["last_error"] is not None
    assert payload["analysis_ready"] is False
    assert payload["detected_language"] == "unknown"
