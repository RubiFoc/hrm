"""Integration tests for vacancy CRUD and pipeline transition APIs."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


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
    candidate_1_id = str(uuid5(NAMESPACE_URL, "candidate-1"))
    candidate_2_id = str(uuid5(NAMESPACE_URL, "candidate-2"))
    with Session(engine) as session:
        session.add(
            CandidateProfile(
                candidate_id=candidate_1_id,
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
                candidate_id=candidate_2_id,
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
        yield app, context_holder, sqlite_database_url, candidate_1_id, candidate_2_id
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


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for vacancy integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_vacancy_crud_and_pipeline_transitions(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify vacancy CRUD and canonical pipeline transitions."""
    _, _, _, candidate_1_id, candidate_2_id = configured_app

    create_response = await api_client.post(
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

    list_response = await api_client.get("/api/v1/vacancies")
    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1

    get_response = await api_client.get(f"/api/v1/vacancies/{vacancy_id}")
    assert get_response.status_code == 200

    patch_response = await api_client.patch(
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
        transition = await api_client.post(
            "/api/v1/pipeline/transitions",
            json={
                "vacancy_id": vacancy_id,
                "candidate_id": candidate_1_id,
                "to_stage": stage,
                "reason": "progress",
            },
        )
        assert transition.status_code == 200

    invalid_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": candidate_2_id,
            "to_stage": "offer",
            "reason": "skip",
        },
    )
    assert invalid_transition.status_code == 422
    assert "not allowed" in invalid_transition.json()["detail"]


async def test_pipeline_transition_rbac_deny_is_audited(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify pipeline transition deny path records RBAC audit event."""
    _, context_holder, database_url, candidate_1_id, _ = configured_app

    create_response = await api_client.post(
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
    denied_response = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": candidate_1_id,
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


async def test_vacancy_and_pipeline_uuid_boundaries_reject_invalid_ids(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify vacancy and pipeline endpoints reject non-UUID identifiers with 422."""
    _, _, _, candidate_1_id, _ = configured_app
    invalid_vacancy_id = "vacancy-not-uuid"

    get_response = await api_client.get(f"/api/v1/vacancies/{invalid_vacancy_id}")
    assert get_response.status_code == 422

    patch_response = await api_client.patch(
        f"/api/v1/vacancies/{invalid_vacancy_id}",
        json={"status": "open"},
    )
    assert patch_response.status_code == 422

    content = b"public-apply-boundary"
    checksum = hashlib.sha256(content).hexdigest()
    apply_response = await api_client.post(
        f"/api/v1/vacancies/{invalid_vacancy_id}/applications",
        data={
            "first_name": "Boundary",
            "last_name": "Case",
            "email": "boundary@example.com",
            "phone": "+375291112233",
            "checksum_sha256": checksum,
        },
        files={"file": ("cv.pdf", content, "application/pdf")},
    )
    assert apply_response.status_code == 422

    invalid_vacancy_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": invalid_vacancy_id,
            "candidate_id": candidate_1_id,
            "to_stage": "applied",
            "reason": "invalid-vacancy-id",
        },
    )
    assert invalid_vacancy_transition.status_code == 422

    create_response = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "UUID Boundary Vacancy",
            "description": "Boundary checks",
            "department": "QA",
            "status": "open",
        },
    )
    assert create_response.status_code == 200
    vacancy_id = create_response.json()["vacancy_id"]

    invalid_candidate_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": "candidate-not-uuid",
            "to_stage": "applied",
            "reason": "invalid-candidate-id",
        },
    )
    assert invalid_candidate_transition.status_code == 422


async def test_openapi_exposes_uuid_format_for_normalized_id_contracts(
    api_client: AsyncClient,
) -> None:
    """Verify OpenAPI reflects UUID typing for normalized API identifiers."""
    response = await api_client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()

    schemas = spec["components"]["schemas"]
    assert schemas["CandidateResponse"]["properties"]["candidate_id"]["format"] == "uuid"
    assert schemas["CVParsingStatusResponse"]["properties"]["candidate_id"]["format"] == "uuid"
    assert schemas["CVParsingStatusResponse"]["properties"]["document_id"]["format"] == "uuid"
    assert schemas["CVParsingStatusResponse"]["properties"]["job_id"]["format"] == "uuid"
    assert schemas["CVAnalysisResponse"]["properties"]["candidate_id"]["format"] == "uuid"
    assert schemas["CVAnalysisResponse"]["properties"]["document_id"]["format"] == "uuid"
    assert schemas["VacancyResponse"]["properties"]["vacancy_id"]["format"] == "uuid"
    assert (
        schemas["PipelineTransitionCreateRequest"]["properties"]["vacancy_id"]["format"] == "uuid"
    )
    assert (
        schemas["PipelineTransitionCreateRequest"]["properties"]["candidate_id"]["format"]
        == "uuid"
    )
    assert (
        schemas["PipelineTransitionResponse"]["properties"]["transition_id"]["format"] == "uuid"
    )

    vacancy_get_parameters = spec["paths"]["/api/v1/vacancies/{vacancy_id}"]["get"]["parameters"]
    candidate_get_parameters = spec["paths"]["/api/v1/candidates/{candidate_id}"]["get"][
        "parameters"
    ]
    candidate_analysis_get_parameters = spec["paths"][
        "/api/v1/candidates/{candidate_id}/cv/analysis"
    ]["get"]["parameters"]
    assert any(
        parameter["name"] == "vacancy_id"
        and parameter["schema"].get("format") == "uuid"
        for parameter in vacancy_get_parameters
    )
    assert any(
        parameter["name"] == "candidate_id"
        and parameter["schema"].get("format") == "uuid"
        for parameter in candidate_get_parameters
    )
    assert any(
        parameter["name"] == "candidate_id"
        and parameter["schema"].get("format") == "uuid"
        for parameter in candidate_analysis_get_parameters
    )
