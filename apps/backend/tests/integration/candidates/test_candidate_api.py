"""Integration tests for candidate CRUD and CV upload/download APIs."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dependencies.candidates import get_candidate_storage
from hrm_backend.candidates.models.document import CandidateDocument
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition

pytestmark = pytest.mark.anyio


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


def _set_candidate_updated_at(
    database_url: str,
    *,
    candidate_id: str,
    updated_at: datetime,
) -> None:
    """Force deterministic candidate ordering for pagination assertions."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            profile = session.get(CandidateProfile, candidate_id)
            assert profile is not None
            profile.updated_at = updated_at
            session.add(profile)
            session.commit()
    finally:
        engine.dispose()


def _seed_candidate_document(
    database_url: str,
    *,
    candidate_id: str,
    parsed_profile_json: dict[str, object] | None,
    detected_language: str = "en",
    parsed_at: datetime | None = None,
) -> None:
    """Seed one active candidate document row for list API filtering tests."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                CandidateDocument(
                    document_id=str(uuid4()),
                    candidate_id=candidate_id,
                    object_key=f"candidates/{candidate_id}/cv/{uuid4()}.pdf",
                    filename="cv.pdf",
                    mime_type="application/pdf",
                    size_bytes=128,
                    checksum_sha256=hashlib.sha256(candidate_id.encode("utf-8")).hexdigest(),
                    is_active=True,
                    parsed_profile_json=parsed_profile_json,
                    evidence_json=None,
                    detected_language=detected_language,
                    parsed_at=parsed_at,
                    created_at=parsed_at or datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
                )
            )
            session.commit()
    finally:
        engine.dispose()


def _seed_pipeline_transition(
    database_url: str,
    *,
    vacancy_id: str,
    candidate_id: str,
    from_stage: str | None,
    to_stage: str,
    transitioned_at: datetime,
) -> None:
    """Seed one append-only vacancy transition row for candidate list context tests."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                PipelineTransition(
                    transition_id=str(uuid4()),
                    vacancy_id=vacancy_id,
                    candidate_id=candidate_id,
                    from_stage=from_stage,
                    to_stage=to_stage,
                    reason="seeded-for-list-tests",
                    changed_by_sub="hr",
                    changed_by_role="hr",
                    transitioned_at=transitioned_at,
                )
            )
            session.commit()
    finally:
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for candidate integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_candidate_crud_and_ownership_deny_are_enforced(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify candidate CRUD with RBAC deny trace for non-privileged staff role."""
    _, context_holder, _, database_url = configured_app

    create_response = await api_client.post(
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

    get_response = await api_client.get(f"/api/v1/candidates/{candidate_id}")
    assert get_response.status_code == 200

    patch_response = await api_client.patch(
        f"/api/v1/candidates/{candidate_id}",
        json={"current_title": "Senior Backend Engineer"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["current_title"] == "Senior Backend Engineer"

    context_holder["context"] = AuthContext(
        subject_id=uuid5(NAMESPACE_URL, "manager-ctx"),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    forbidden_get = await api_client.get(f"/api/v1/candidates/{candidate_id}")
    assert forbidden_get.status_code == 403

    forbidden_list = await api_client.get("/api/v1/candidates")
    assert forbidden_list.status_code == 403

    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="hr",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    list_response = await api_client.get("/api/v1/candidates")
    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1
    assert list_response.json()["total"] == 1
    assert list_response.json()["limit"] == 20
    assert list_response.json()["offset"] == 0

    events = _load_events(database_url)
    permission_denials = [
        event
        for event in events
        if event.action == "candidate_profile:read" and event.result == "denied"
    ]
    assert len(permission_denials) == 1
    assert permission_denials[0].actor_role == "manager"
    assert "has no permission" in (permission_denials[0].reason or "")


async def test_cv_upload_download_status_and_validation_failures(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify CV upload/download/status and validation error contracts."""
    _, context_holder, _, _ = configured_app

    create_response = await api_client.post(
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
    upload_response = await api_client.post(
        f"/api/v1/candidates/{candidate_id}/cv",
        data={"checksum_sha256": valid_checksum},
        files={"file": ("cv.pdf", valid_content, "application/pdf")},
    )
    assert upload_response.status_code == 200
    upload_payload = upload_response.json()
    assert upload_payload["size_bytes"] == len(valid_content)

    download_response = await api_client.get(f"/api/v1/candidates/{candidate_id}/cv")
    assert download_response.status_code == 200
    assert download_response.content == valid_content
    assert "attachment; filename=\"cv.pdf\"" in download_response.headers["content-disposition"]

    status_response = await api_client.get(f"/api/v1/candidates/{candidate_id}/cv/parsing-status")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == "queued"
    assert status_payload["analysis_ready"] is False
    assert status_payload["detected_language"] == "unknown"

    analysis_not_ready = await api_client.get(f"/api/v1/candidates/{candidate_id}/cv/analysis")
    assert analysis_not_ready.status_code == 409

    bad_mime_content = b"plain-text"
    bad_mime_checksum = hashlib.sha256(bad_mime_content).hexdigest()
    bad_mime_response = await api_client.post(
        f"/api/v1/candidates/{candidate_id}/cv",
        data={"checksum_sha256": bad_mime_checksum},
        files={"file": ("cv.txt", bad_mime_content, "text/plain")},
    )
    assert bad_mime_response.status_code == 415

    bad_checksum_response = await api_client.post(
        f"/api/v1/candidates/{candidate_id}/cv",
        data={"checksum_sha256": "0" * 64},
        files={"file": ("cv.pdf", valid_content, "application/pdf")},
    )
    assert bad_checksum_response.status_code == 422

    oversized_content = b"x" * 33
    oversized_checksum = hashlib.sha256(oversized_content).hexdigest()
    oversized_response = await api_client.post(
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
    denied_status = await api_client.get(f"/api/v1/candidates/{candidate_id}/cv/parsing-status")
    assert denied_status.status_code == 403
    denied_analysis = await api_client.get(f"/api/v1/candidates/{candidate_id}/cv/analysis")
    assert denied_analysis.status_code == 403


async def test_candidate_uuid_boundaries_reject_invalid_ids(
    api_client: AsyncClient,
) -> None:
    """Verify candidate endpoints reject non-UUID path identifiers with 422."""
    invalid_id = "candidate-not-uuid"

    get_response = await api_client.get(f"/api/v1/candidates/{invalid_id}")
    assert get_response.status_code == 422

    content = b"uuid-boundary-cv"
    checksum = hashlib.sha256(content).hexdigest()
    upload_response = await api_client.post(
        f"/api/v1/candidates/{invalid_id}/cv",
        data={"checksum_sha256": checksum},
        files={"file": ("cv.pdf", content, "application/pdf")},
    )
    assert upload_response.status_code == 422

    status_response = await api_client.get(f"/api/v1/candidates/{invalid_id}/cv/parsing-status")
    assert status_response.status_code == 422

    analysis_response = await api_client.get(f"/api/v1/candidates/{invalid_id}/cv/analysis")
    assert analysis_response.status_code == 422


async def test_candidate_list_supports_search_filters_and_pagination(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify recruiter-facing candidate list filtering, enrichment, and pagination contract."""
    _, _, _, database_url = configured_app

    alpha_response = await api_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Alice",
            "last_name": "Miller",
            "email": "alice@example.com",
            "location": "Minsk",
            "current_title": "Backend Recruiter",
            "extra_data": {},
        },
    )
    beta_response = await api_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Boris",
            "last_name": "Stone",
            "email": "boris@example.com",
            "location": "Minsk",
            "current_title": "Backend Recruiter",
            "extra_data": {},
        },
    )
    gamma_response = await api_client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Carla",
            "last_name": "West",
            "email": "carla@example.com",
            "location": "Warsaw",
            "current_title": "Designer",
            "extra_data": {},
        },
    )
    alpha_id = alpha_response.json()["candidate_id"]
    beta_id = beta_response.json()["candidate_id"]
    gamma_id = gamma_response.json()["candidate_id"]

    _seed_candidate_document(
        database_url,
        candidate_id=alpha_id,
        parsed_profile_json={
            "summary": "Leads Acme Logistics recruiting and warehouse staffing operations.",
            "skills": ["python", "talent_sourcing"],
            "experience": {"years_total": 6},
            "workplaces": {
                "entries": [
                    {
                        "employer": "Acme Logistics",
                        "position": {
                            "raw": "Warehouse Supervisor",
                            "normalized": "warehouse supervisor",
                        },
                    }
                ]
            },
            "titles": {
                "current": {
                    "raw": "Backend Recruiter",
                    "normalized": "backend recruiter",
                },
                "past": [],
            },
        },
        detected_language="en",
        parsed_at=datetime(2026, 3, 12, 8, 30, tzinfo=UTC),
    )
    _seed_candidate_document(
        database_url,
        candidate_id=beta_id,
        parsed_profile_json={
            "summary": "Supports office hiring operations.",
            "skills": ["python"],
            "experience": {"years_total": 2},
            "workplaces": {
                "entries": [
                    {
                        "employer": "People Ops",
                        "position": {
                            "raw": "Recruiter",
                            "normalized": "recruiter",
                        },
                    }
                ]
            },
            "titles": {
                "current": {"raw": "Backend Recruiter", "normalized": "backend recruiter"},
                "past": [],
            },
        },
        detected_language="en",
        parsed_at=datetime(2026, 3, 12, 8, 0, tzinfo=UTC),
    )
    _seed_candidate_document(
        database_url,
        candidate_id=gamma_id,
        parsed_profile_json=None,
        detected_language="unknown",
        parsed_at=None,
    )

    _set_candidate_updated_at(
        database_url,
        candidate_id=alpha_id,
        updated_at=datetime(2026, 3, 12, 13, 0, tzinfo=UTC),
    )
    _set_candidate_updated_at(
        database_url,
        candidate_id=beta_id,
        updated_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
    )
    _set_candidate_updated_at(
        database_url,
        candidate_id=gamma_id,
        updated_at=datetime(2026, 3, 12, 11, 0, tzinfo=UTC),
    )

    filtered_response = await api_client.get(
        "/api/v1/candidates",
        params={
            "search": "acme logistics",
            "location": "minsk",
            "current_title": "backend recruit",
            "skill": "python",
            "analysis_ready": "true",
            "min_years_experience": "5",
            "limit": "20",
            "offset": "0",
        },
    )
    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert filtered_payload["total"] == 1
    assert filtered_payload["limit"] == 20
    assert filtered_payload["offset"] == 0
    assert [item["candidate_id"] for item in filtered_payload["items"]] == [alpha_id]
    assert filtered_payload["items"][0]["analysis_ready"] is True
    assert filtered_payload["items"][0]["detected_language"] == "en"
    assert filtered_payload["items"][0]["years_experience"] == 6
    assert filtered_payload["items"][0]["skills"] == ["python", "talent_sourcing"]
    assert filtered_payload["items"][0]["vacancy_stage"] is None
    assert filtered_payload["items"][0]["parsed_at"].startswith("2026-03-12T08:30:00")

    pagination_response = await api_client.get(
        "/api/v1/candidates",
        params={"limit": "1", "offset": "1"},
    )
    assert pagination_response.status_code == 200
    pagination_payload = pagination_response.json()
    assert pagination_payload["total"] == 3
    assert pagination_payload["limit"] == 1
    assert pagination_payload["offset"] == 1
    assert [item["candidate_id"] for item in pagination_payload["items"]] == [beta_id]


async def test_candidate_list_supports_vacancy_context_stage_filters_and_pipeline_only(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify candidate list resolves latest vacancy stages and vacancy-scoped filters."""
    _, _, _, database_url = configured_app

    vacancy_response = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "Recruiter",
            "description": "Own candidate screening and pipeline operations.",
            "department": "HR",
            "status": "open",
        },
    )
    assert vacancy_response.status_code == 200
    vacancy_id = vacancy_response.json()["vacancy_id"]

    alpha_id = (
        await api_client.post(
            "/api/v1/candidates",
            json={
                "first_name": "Alice",
                "last_name": "Stage",
                "email": "alice.stage@example.com",
                "extra_data": {},
            },
        )
    ).json()["candidate_id"]
    beta_id = (
        await api_client.post(
            "/api/v1/candidates",
            json={
                "first_name": "Boris",
                "last_name": "Stage",
                "email": "boris.stage@example.com",
                "extra_data": {},
            },
        )
    ).json()["candidate_id"]
    gamma_id = (
        await api_client.post(
            "/api/v1/candidates",
            json={
                "first_name": "Carla",
                "last_name": "Stage",
                "email": "carla.stage@example.com",
                "extra_data": {},
            },
        )
    ).json()["candidate_id"]

    _seed_pipeline_transition(
        database_url,
        vacancy_id=vacancy_id,
        candidate_id=alpha_id,
        from_stage=None,
        to_stage="applied",
        transitioned_at=datetime(2026, 3, 12, 8, 0, tzinfo=UTC),
    )
    _seed_pipeline_transition(
        database_url,
        vacancy_id=vacancy_id,
        candidate_id=alpha_id,
        from_stage="applied",
        to_stage="shortlist",
        transitioned_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
    )
    _seed_pipeline_transition(
        database_url,
        vacancy_id=vacancy_id,
        candidate_id=beta_id,
        from_stage=None,
        to_stage="screening",
        transitioned_at=datetime(2026, 3, 12, 8, 30, tzinfo=UTC),
    )

    context_response = await api_client.get(
        "/api/v1/candidates",
        params={"vacancy_id": vacancy_id},
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    context_items = {
        item["candidate_id"]: item["vacancy_stage"]
        for item in context_payload["items"]
    }
    assert context_items[alpha_id] == "shortlist"
    assert context_items[beta_id] == "screening"
    assert context_items[gamma_id] is None

    pipeline_only_response = await api_client.get(
        "/api/v1/candidates",
        params={"vacancy_id": vacancy_id, "in_pipeline_only": "true"},
    )
    assert pipeline_only_response.status_code == 200
    assert {
        item["candidate_id"] for item in pipeline_only_response.json()["items"]
    } == {alpha_id, beta_id}

    shortlist_response = await api_client.get(
        "/api/v1/candidates",
        params={"vacancy_id": vacancy_id, "stage": "shortlist"},
    )
    assert shortlist_response.status_code == 200
    shortlist_payload = shortlist_response.json()
    assert shortlist_payload["total"] == 1
    assert [item["candidate_id"] for item in shortlist_payload["items"]] == [alpha_id]
    assert shortlist_payload["items"][0]["vacancy_stage"] == "shortlist"


async def test_candidate_list_rejects_vacancy_stage_filters_without_vacancy_context(
    api_client: AsyncClient,
) -> None:
    """Verify vacancy-scoped stage filters return `422` without `vacancy_id`."""
    stage_response = await api_client.get(
        "/api/v1/candidates",
        params={"stage": "screening"},
    )
    assert stage_response.status_code == 422
    assert stage_response.json()["detail"] == "stage_requires_vacancy_id"

    in_pipeline_response = await api_client.get(
        "/api/v1/candidates",
        params={"in_pipeline_only": "true"},
    )
    assert in_pipeline_response.status_code == 422
    assert in_pipeline_response.json()["detail"] == "in_pipeline_only_requires_vacancy_id"
