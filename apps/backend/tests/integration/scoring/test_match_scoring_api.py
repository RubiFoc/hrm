"""Integration tests for match scoring API and worker lifecycle."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import anyio.to_thread
import fastapi.concurrency
import pytest
import starlette.concurrency
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.audit.dao.audit_event_dao import AuditEventDAO
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.candidates.dao.cv_parsing_job_dao import CVParsingJobDAO
from hrm_backend.candidates.dependencies.candidates import get_candidate_storage
from hrm_backend.candidates.services import candidate_service as candidate_service_module
from hrm_backend.candidates.services.cv_parsing_worker_service import CVParsingWorkerService
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.scoring.dao.match_score_artifact_dao import MatchScoreArtifactDAO
from hrm_backend.scoring.dao.match_scoring_job_dao import MatchScoringJobDAO
from hrm_backend.scoring.dependencies.scoring import get_match_scoring_adapter
from hrm_backend.scoring.services import match_scoring_service as match_scoring_service_module
from hrm_backend.scoring.services.match_scoring_worker_service import MatchScoringWorkerService
from hrm_backend.scoring.utils.result import MatchScoreResult
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO

pytestmark = pytest.mark.anyio
FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "candidates"


def _read_fixture_bytes(filename: str) -> bytes:
    """Read one CV fixture payload by filename."""
    return (FIXTURES_DIR / filename).read_bytes()


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


class FakeMatchScoringAdapter:
    """Deterministic scoring adapter for integration tests."""

    def __init__(self) -> None:
        self.payload = MatchScoreResult.model_validate(
            {
                "score": 91,
                "confidence": 0.84,
                "summary": "Strong shortlist fit based on Python, APIs, and Docker evidence.",
                "matched_requirements": ["Python", "REST APIs", "Docker"],
                "missing_requirements": ["Kubernetes"],
                "evidence": [
                    {
                        "requirement": "Python",
                        "snippet": "5 years of Python backend engineering",
                        "source_field": "skills",
                    },
                    {
                        "requirement": "Docker",
                        "snippet": "Dockerized deployment ownership",
                        "source_field": "summary",
                    },
                ],
                "model_name": "llama3.2",
                "model_version": "latest",
            }
        )
        self.should_fail = False

    def score_candidate(self, **_: object) -> MatchScoreResult:
        if self.should_fail:
            raise RuntimeError("Ollama scoring failed by deterministic test marker")
        return self.payload


@pytest.fixture()
def anyio_backend() -> str:
    """Pin integration tests to asyncio backend to avoid trio threadpool deadlocks."""
    return "asyncio"


@pytest.fixture(autouse=True)
def inline_threadpool_patch():
    """Avoid AnyIO threadpool deadlocks in in-process ASGI integration requests."""
    original_anyio_run_sync = anyio.to_thread.run_sync
    original_starlette_run_in_threadpool = starlette.concurrency.run_in_threadpool
    original_fastapi_run_in_threadpool = fastapi.concurrency.run_in_threadpool

    async def _run_sync_inline(func, /, *args, **_: object):
        return func(*args)

    async def _run_in_threadpool_inline(func, /, *args, **kwargs: object):
        if kwargs:
            return func(*args, **kwargs)
        return func(*args)

    anyio.to_thread.run_sync = _run_sync_inline
    starlette.concurrency.run_in_threadpool = _run_in_threadpool_inline
    fastapi.concurrency.run_in_threadpool = _run_in_threadpool_inline
    try:
        yield
    finally:
        anyio.to_thread.run_sync = original_anyio_run_sync
        starlette.concurrency.run_in_threadpool = original_starlette_run_in_threadpool
        fastapi.concurrency.run_in_threadpool = original_fastapi_run_in_threadpool


@pytest.fixture(autouse=True)
def disable_celery_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace Celery dispatch with no-op helpers inside integration tests."""
    monkeypatch.setattr(candidate_service_module, "enqueue_cv_parsing", lambda **_: None)
    monkeypatch.setattr(match_scoring_service_module, "enqueue_match_scoring", lambda **_: None)


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'match_scoring.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure application dependency overrides for match scoring integration tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
        cv_max_size_bytes=4096,
        cv_parsing_max_attempts=2,
        match_scoring_max_attempts=2,
        scoring_low_confidence_threshold=0.7,
    )
    storage = InMemoryCandidateStorage()
    adapter = FakeMatchScoringAdapter()
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

    def _get_adapter_override() -> FakeMatchScoringAdapter:
        return adapter

    app.dependency_overrides[get_settings] = _get_settings_override
    app.dependency_overrides[get_current_auth_context] = _get_auth_context_override
    app.dependency_overrides[get_candidate_storage] = _get_storage_override
    app.dependency_overrides[get_match_scoring_adapter] = _get_adapter_override

    engine = create_engine(sqlite_database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        yield app, settings, context_holder, storage, adapter, sqlite_database_url
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_candidate_storage, None)
        app.dependency_overrides.pop(get_match_scoring_adapter, None)
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for match scoring integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


def _run_parsing_worker_once(
    database_url: str,
    settings: AppSettings,
    storage: InMemoryCandidateStorage,
) -> str:
    """Run one parsing worker iteration and return terminal status."""
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


def _run_scoring_worker_once(
    database_url: str,
    settings: AppSettings,
    adapter: FakeMatchScoringAdapter,
    *,
    vacancy_id: str,
    candidate_id: str,
) -> str:
    """Run worker for the latest job of one vacancy-candidate pair and return terminal status."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            scoring_job_dao = MatchScoringJobDAO(session=session)
            latest = scoring_job_dao.get_latest_for_pair(
                vacancy_id=vacancy_id,
                candidate_id=candidate_id,
            )
            assert latest is not None
            worker = MatchScoringWorkerService(
                settings=settings,
                scoring_job_dao=scoring_job_dao,
                score_artifact_dao=MatchScoreArtifactDAO(session=session),
                vacancy_dao=VacancyDAO(session=session),
                candidate_profile_dao=CandidateProfileDAO(session=session),
                document_dao=CandidateDocumentDAO(session=session),
                adapter=adapter,  # type: ignore[arg-type]
                audit_service=AuditService(dao=AuditEventDAO(session=session)),
            )
            return worker.process_job_by_id(job_id=latest.job_id).status
    finally:
        engine.dispose()


def _claim_latest_scoring_job_running(
    database_url: str,
    settings: AppSettings,
    *,
    vacancy_id: str,
    candidate_id: str,
) -> str:
    """Claim latest job into running state and return its id."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            dao = MatchScoringJobDAO(session=session)
            latest = dao.get_latest_for_pair(vacancy_id=vacancy_id, candidate_id=candidate_id)
            assert latest is not None
            claimed = dao.claim_job_by_id(
                job_id=latest.job_id,
                max_attempts=settings.match_scoring_max_attempts,
            )
            assert claimed is not None
            return claimed.job_id
    finally:
        engine.dispose()


def _mark_latest_scoring_job_failed(
    database_url: str,
    *,
    vacancy_id: str,
    candidate_id: str,
) -> str:
    """Mark latest scoring job failed and return its id."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            dao = MatchScoringJobDAO(session=session)
            latest = dao.get_latest_for_pair(vacancy_id=vacancy_id, candidate_id=candidate_id)
            assert latest is not None
            dao.mark_failed(latest, error_text="Ollama scoring failed by deterministic test marker")
            return latest.job_id
    finally:
        engine.dispose()


async def _create_scoring_fixture(
    api_client: AsyncClient,
    *,
    fixture_name: str = "sample_cv_en.pdf",
    filename: str = "cv.pdf",
    mime_type: str = "application/pdf",
) -> tuple[str, str]:
    """Create vacancy and candidate, upload CV, and return identifiers."""
    vacancy_response = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "Backend Engineer",
            "description": "Build APIs and platform services",
            "department": "Engineering",
            "status": "open",
        },
    )
    assert vacancy_response.status_code == 200
    vacancy_id = vacancy_response.json()["vacancy_id"]

    candidate_response = await api_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Jane",
            "last_name": "Stone",
            "email": "jane@example.com",
            "extra_data": {},
        },
    )
    assert candidate_response.status_code == 200
    candidate_id = candidate_response.json()["candidate_id"]

    content = _read_fixture_bytes(fixture_name)
    checksum = hashlib.sha256(content).hexdigest()
    upload_response = await api_client.post(
        f"/api/v1/candidates/{candidate_id}/cv",
        data={"checksum_sha256": checksum},
        files={"file": (filename, content, mime_type)},
    )
    assert upload_response.status_code == 200
    return vacancy_id, candidate_id


async def test_match_scoring_rejects_enqueue_when_cv_analysis_is_not_ready(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify scoring enqueue is blocked with 409 until parsed CV analysis exists."""
    vacancy_id, candidate_id = await _create_scoring_fixture(api_client)

    response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/match-scores",
        json={"candidate_id": candidate_id},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "CV analysis is not ready"


async def test_match_scoring_lifecycle_covers_queued_running_failed_and_succeeded(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify scoring API exposes queued, running, failed, and succeeded states."""
    _, settings, _, storage, adapter, database_url = configured_app
    vacancy_id, candidate_id = await _create_scoring_fixture(api_client)
    assert _run_parsing_worker_once(database_url, settings, storage) == "succeeded"

    queued = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/match-scores",
        json={"candidate_id": candidate_id},
    )
    assert queued.status_code == 200
    assert queued.json()["status"] == "queued"

    _claim_latest_scoring_job_running(
        database_url,
        settings,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
    )
    running = await api_client.get(
        f"/api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}"
    )
    assert running.status_code == 200
    assert running.json()["status"] == "running"

    _mark_latest_scoring_job_failed(
        database_url,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
    )
    failed = await api_client.get(
        f"/api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}"
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"

    requeued = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/match-scores",
        json={"candidate_id": candidate_id},
    )
    assert requeued.status_code == 200
    assert requeued.json()["status"] == "queued"

    adapter.should_fail = False
    assert _run_scoring_worker_once(
        database_url,
        settings,
        adapter,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
    ) == "succeeded"

    succeeded = await api_client.get(
        f"/api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}"
    )
    assert succeeded.status_code == 200
    assert succeeded.json()["status"] == "succeeded"
    assert succeeded.json()["score"] == 91


async def test_match_scoring_payload_propagates_evidence_and_can_list_latest_entries(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify latest score payload shape includes evidence and model metadata for UI rendering."""
    _, settings, _, storage, adapter, database_url = configured_app
    vacancy_id, candidate_id = await _create_scoring_fixture(api_client)
    assert _run_parsing_worker_once(database_url, settings, storage) == "succeeded"

    create_response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/match-scores",
        json={"candidate_id": candidate_id},
    )
    assert create_response.status_code == 200
    assert _run_scoring_worker_once(
        database_url,
        settings,
        adapter,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
    ) == "succeeded"

    latest_create_response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/match-scores",
        json={"candidate_id": candidate_id},
    )
    assert latest_create_response.status_code == 200
    latest_create_payload = latest_create_response.json()
    assert latest_create_payload["status"] == "succeeded"
    assert latest_create_payload["requires_manual_review"] is False
    assert latest_create_payload["manual_review_reason"] is None
    assert latest_create_payload["confidence_threshold"] == 0.7

    get_response = await api_client.get(
        f"/api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}"
    )
    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["vacancy_id"] == vacancy_id
    assert payload["candidate_id"] == candidate_id
    assert payload["status"] == "succeeded"
    assert payload["confidence"] == 0.84
    assert payload["requires_manual_review"] is False
    assert payload["manual_review_reason"] is None
    assert payload["confidence_threshold"] == 0.7
    assert payload["summary"]
    assert payload["matched_requirements"] == ["Python", "REST APIs", "Docker"]
    assert payload["missing_requirements"] == ["Kubernetes"]
    assert payload["evidence"][0]["requirement"] == "Python"
    assert payload["evidence"][0]["snippet"] == "5 years of Python backend engineering"
    assert payload["model_name"] == "llama3.2"
    assert payload["model_version"] == "latest"
    assert payload["scored_at"] is not None

    list_response = await api_client.get(f"/api/v1/vacancies/{vacancy_id}/match-scores")
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["candidate_id"] == candidate_id
    assert items[0]["requires_manual_review"] is False
    assert items[0]["confidence_threshold"] == 0.7


async def test_match_scoring_low_confidence_success_returns_manual_review_metadata(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify low-confidence succeeded scores return additive manual-review flags."""
    _, settings, _, storage, adapter, database_url = configured_app
    adapter.payload = adapter.payload.model_copy(update={"confidence": 0.69})
    vacancy_id, candidate_id = await _create_scoring_fixture(api_client)
    assert _run_parsing_worker_once(database_url, settings, storage) == "succeeded"

    create_response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/match-scores",
        json={"candidate_id": candidate_id},
    )
    assert create_response.status_code == 200
    assert create_response.json()["status"] == "queued"
    assert _run_scoring_worker_once(
        database_url,
        settings,
        adapter,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
    ) == "succeeded"

    latest_create_response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/match-scores",
        json={"candidate_id": candidate_id},
    )
    assert latest_create_response.status_code == 200
    latest_create_payload = latest_create_response.json()
    assert latest_create_payload["status"] == "succeeded"
    assert latest_create_payload["requires_manual_review"] is True
    assert latest_create_payload["manual_review_reason"] == "low_confidence"
    assert latest_create_payload["confidence_threshold"] == 0.7

    get_response = await api_client.get(
        f"/api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}"
    )
    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["status"] == "succeeded"
    assert payload["confidence"] == 0.69
    assert payload["requires_manual_review"] is True
    assert payload["manual_review_reason"] == "low_confidence"
    assert payload["confidence_threshold"] == 0.7


async def test_match_scoring_accepts_enriched_parsed_profile_without_contract_changes(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify scoring flow stays compatible when parsed CV contains workplaces and education."""
    _, settings, _, storage, adapter, database_url = configured_app
    vacancy_id, candidate_id = await _create_scoring_fixture(
        api_client,
        fixture_name="sample_cv_structured_en.pdf",
        filename="structured.pdf",
        mime_type="application/pdf",
    )
    assert _run_parsing_worker_once(database_url, settings, storage) == "succeeded"

    analysis_response = await api_client.get(f"/api/v1/candidates/{candidate_id}/cv/analysis")
    assert analysis_response.status_code == 200
    parsed_profile = analysis_response.json()["parsed_profile"]
    assert parsed_profile["workplaces"]["entries"]
    assert parsed_profile["education"]["entries"]
    assert parsed_profile["titles"]["current"]["raw"] == "Warehouse Supervisor"

    create_response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/match-scores",
        json={"candidate_id": candidate_id},
    )
    assert create_response.status_code == 200
    assert create_response.json()["status"] == "queued"

    assert _run_scoring_worker_once(
        database_url,
        settings,
        adapter,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
    ) == "succeeded"

    score_response = await api_client.get(
        f"/api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}"
    )
    assert score_response.status_code == 200
    assert score_response.json()["status"] == "succeeded"
