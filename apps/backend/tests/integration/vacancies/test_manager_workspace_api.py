"""Integration tests for manager workspace vacancy visibility APIs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.models.document import CandidateDocument
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.interviews.models.interview import Interview
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for manager workspace integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'manager_workspace.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for manager workspace integration tests."""
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
        yield app, context_holder, engine
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for manager workspace integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


def _seed_staff_accounts(engine) -> dict[str, str]:
    """Insert manager and non-manager staff accounts used by assignment resolution tests."""
    manager_alpha_id = "11111111-1111-4111-8111-111111111111"
    manager_beta_id = "22222222-2222-4222-8222-222222222222"
    inactive_manager_id = "33333333-3333-4333-8333-333333333333"
    with Session(engine) as session:
        session.add_all(
            [
                StaffAccount(
                    staff_id=manager_alpha_id,
                    login="manager-alpha",
                    email="manager-alpha@example.com",
                    password_hash="hash",
                    role="manager",
                    is_active=True,
                ),
                StaffAccount(
                    staff_id=manager_beta_id,
                    login="manager-beta",
                    email="manager-beta@example.com",
                    password_hash="hash",
                    role="manager",
                    is_active=True,
                ),
                StaffAccount(
                    staff_id=inactive_manager_id,
                    login="manager-gamma",
                    email="manager-gamma@example.com",
                    password_hash="hash",
                    role="manager",
                    is_active=False,
                ),
                StaffAccount(
                    staff_id="44444444-4444-4444-8444-444444444444",
                    login="hr-user",
                    email="hr@example.com",
                    password_hash="hash",
                    role="hr",
                    is_active=True,
                ),
            ]
        )
        session.commit()
    return {
        "manager_alpha_id": manager_alpha_id,
        "manager_beta_id": manager_beta_id,
        "inactive_manager_id": inactive_manager_id,
    }


def _seed_candidate(session: Session, *, candidate_id: str, suffix: str) -> None:
    """Insert one candidate profile row for manager workspace visibility tests."""
    session.add(
        CandidateProfile(
            candidate_id=candidate_id,
            owner_subject_id=f"candidate-{suffix}",
            first_name=suffix.title(),
            last_name="Candidate",
            email=f"{suffix}@example.com",
            phone=None,
            location="Minsk",
            current_title="Engineer",
            extra_data={},
            updated_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
        )
    )


def _seed_transition(
    session: Session,
    *,
    transition_id: str,
    vacancy_id: str,
    candidate_id: str,
    to_stage: str,
    transitioned_at: datetime,
) -> None:
    """Insert one pipeline transition row directly for snapshot tests."""
    session.add(
        PipelineTransition(
            transition_id=transition_id,
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            from_stage=None,
            to_stage=to_stage,
            reason="seeded",
            changed_by_sub="hr-seed",
            changed_by_role="hr",
            transitioned_at=transitioned_at,
        )
    )


def _seed_document(
    session: Session,
    *,
    candidate_id: str,
    checksum_seed: str,
    parsed_profile: dict[str, object] | None,
    parsed_at: datetime | None,
) -> None:
    """Insert one active candidate document row for snapshot enrichment tests."""
    session.add(
        CandidateDocument(
            candidate_id=candidate_id,
            object_key=f"cv/{candidate_id}.pdf",
            filename=f"{candidate_id}.pdf",
            mime_type="application/pdf",
            size_bytes=128,
            checksum_sha256=checksum_seed * 64,
            is_active=True,
            parsed_profile_json=parsed_profile,
            evidence_json=[] if parsed_profile is not None else None,
            detected_language="en" if parsed_profile is not None else "unknown",
            parsed_at=parsed_at,
        )
    )


def _seed_interview(
    session: Session,
    *,
    interview_id: str,
    vacancy_id: str,
    candidate_id: str,
    interviewer_staff_id: str,
    scheduled_start_at: datetime,
) -> None:
    """Insert one active interview row for manager workspace summary tests."""
    session.add(
        Interview(
            interview_id=interview_id,
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            status="awaiting_candidate_confirmation",
            calendar_sync_status="synced",
            schedule_version=1,
            scheduled_start_at=scheduled_start_at,
            scheduled_end_at=scheduled_start_at + timedelta(hours=1),
            timezone="Europe/Minsk",
            location_kind="google_meet",
            location_details="meet",
            interviewer_staff_ids_json=[interviewer_staff_id],
            candidate_response_status="pending",
            created_by_staff_id="hr-seed",
            updated_by_staff_id="hr-seed",
            created_at=scheduled_start_at - timedelta(days=1),
            updated_at=scheduled_start_at - timedelta(days=1),
            last_synced_at=scheduled_start_at - timedelta(days=1),
        )
    )


async def test_manager_workspace_endpoints_are_scoped_and_read_only(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify manager overview/snapshot scope and deny access to HR vacancy list APIs."""
    _, context_holder, engine = configured_app
    staff = _seed_staff_accounts(engine)

    create_alpha = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "Platform Engineer",
            "description": "Build platform foundations.",
            "department": "Engineering",
            "status": "open",
            "hiring_manager_login": "manager-alpha",
        },
    )
    assert create_alpha.status_code == 200
    alpha_vacancy_id = create_alpha.json()["vacancy_id"]
    assert create_alpha.json()["hiring_manager_staff_id"] == staff["manager_alpha_id"]
    assert create_alpha.json()["hiring_manager_login"] == "manager-alpha"

    create_beta = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "QA Lead",
            "description": "Own release quality.",
            "department": "Quality",
            "status": "paused",
            "hiring_manager_login": "manager-alpha",
        },
    )
    assert create_beta.status_code == 200
    beta_vacancy_id = create_beta.json()["vacancy_id"]

    create_other = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "Data Engineer",
            "description": "Build reporting pipelines.",
            "department": "Data",
            "status": "open",
            "hiring_manager_login": "manager-beta",
        },
    )
    assert create_other.status_code == 200
    other_vacancy_id = create_other.json()["vacancy_id"]

    with Session(engine) as session:
        _seed_candidate(
            session,
            candidate_id="aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa",
            suffix="ada",
        )
        _seed_candidate(
            session,
            candidate_id="bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb",
            suffix="grace",
        )
        _seed_candidate(
            session,
            candidate_id="cccccccc-3333-4333-8333-cccccccccccc",
            suffix="tim",
        )
        _seed_transition(
            session,
            transition_id="dddddddd-4444-4444-8444-dddddddddddd",
            vacancy_id=alpha_vacancy_id,
            candidate_id="aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa",
            to_stage="screening",
            transitioned_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
        )
        _seed_transition(
            session,
            transition_id="eeeeeeee-5555-4555-8555-eeeeeeeeeeee",
            vacancy_id=alpha_vacancy_id,
            candidate_id="bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb",
            to_stage="shortlist",
            transitioned_at=datetime(2026, 3, 12, 9, 30, tzinfo=UTC),
        )
        _seed_transition(
            session,
            transition_id="ffffffff-6666-4666-8666-ffffffffffff",
            vacancy_id=beta_vacancy_id,
            candidate_id="cccccccc-3333-4333-8333-cccccccccccc",
            to_stage="interview",
            transitioned_at=datetime(2026, 3, 11, 10, 0, tzinfo=UTC),
        )
        _seed_document(
            session,
            candidate_id="aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa",
            checksum_seed="a",
            parsed_profile={"skills": ["python"], "experience": {"years_total": 5}},
            parsed_at=datetime(2026, 3, 12, 8, 45, tzinfo=UTC),
        )
        _seed_document(
            session,
            candidate_id="bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb",
            checksum_seed="b",
            parsed_profile=None,
            parsed_at=None,
        )
        _seed_interview(
            session,
            interview_id="11111111-7777-4777-8777-111111111111",
            vacancy_id=alpha_vacancy_id,
            candidate_id="bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb",
            interviewer_staff_id=staff["manager_alpha_id"],
            scheduled_start_at=datetime.now(UTC) + timedelta(days=1),
        )
        _seed_interview(
            session,
            interview_id="22222222-8888-4888-8888-222222222222",
            vacancy_id=beta_vacancy_id,
            candidate_id="cccccccc-3333-4333-8333-cccccccccccc",
            interviewer_staff_id=staff["manager_alpha_id"],
            scheduled_start_at=datetime.now(UTC) + timedelta(days=2),
        )
        session.add(
            Offer(
                vacancy_id=alpha_vacancy_id,
                candidate_id="aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa",
                status="sent",
                terms_summary="Offer summary.",
                sent_at=datetime(2026, 3, 12, 10, 0, tzinfo=UTC),
                sent_by_staff_id="hr-seed",
                created_at=datetime(2026, 3, 12, 10, 0, tzinfo=UTC),
                updated_at=datetime(2026, 3, 12, 10, 0, tzinfo=UTC),
            )
        )
        session.commit()

    context_holder["context"] = AuthContext(
        subject_id=UUID(staff["manager_alpha_id"]),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    legacy_list_response = await api_client.get("/api/v1/vacancies")
    assert legacy_list_response.status_code == 403

    overview_response = await api_client.get("/api/v1/vacancies/manager-workspace")
    assert overview_response.status_code == 200
    overview_payload = overview_response.json()
    assert overview_payload["summary"]["vacancy_count"] == 2
    assert overview_payload["summary"]["open_vacancy_count"] == 1
    assert overview_payload["summary"]["candidate_count"] == 3
    assert overview_payload["summary"]["active_interview_count"] == 2
    assert [item["vacancy_id"] for item in overview_payload["items"]] == [
        beta_vacancy_id,
        alpha_vacancy_id,
    ]

    snapshot_response = await api_client.get(
        f"/api/v1/vacancies/{alpha_vacancy_id}/manager-workspace/candidates"
    )
    assert snapshot_response.status_code == 200
    snapshot_payload = snapshot_response.json()
    assert snapshot_payload["summary"]["candidate_count"] == 2
    assert snapshot_payload["summary"]["stage_counts"]["screening"] == 1
    assert snapshot_payload["summary"]["stage_counts"]["shortlist"] == 1
    assert [item["candidate_id"] for item in snapshot_payload["items"]] == [
        "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb",
        "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa",
    ]
    assert snapshot_payload["items"][0]["offer_status"] is None
    assert snapshot_payload["items"][1]["offer_status"] == "sent"
    assert "email" not in snapshot_payload["items"][0]
    assert "skills" not in snapshot_payload["items"][0]

    forbidden_snapshot = await api_client.get(
        f"/api/v1/vacancies/{other_vacancy_id}/manager-workspace/candidates"
    )
    assert forbidden_snapshot.status_code == 404
    assert forbidden_snapshot.json()["detail"] == "manager_workspace_vacancy_not_found"


async def test_vacancy_assignment_requires_known_active_manager_login(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify vacancy assignment resolves manager login and rejects invalid manager targets."""
    _, _, engine = configured_app
    _seed_staff_accounts(engine)

    missing_manager = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "Ops Engineer",
            "description": "Own platform operations.",
            "department": "Operations",
            "status": "open",
            "hiring_manager_login": "missing-manager",
        },
    )
    assert missing_manager.status_code == 422
    assert missing_manager.json()["detail"] == "hiring_manager_not_found"

    wrong_role = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "Ops Engineer",
            "description": "Own platform operations.",
            "department": "Operations",
            "status": "open",
            "hiring_manager_login": "hr-user",
        },
    )
    assert wrong_role.status_code == 422
    assert wrong_role.json()["detail"] == "hiring_manager_role_invalid"

    inactive_manager = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "Ops Engineer",
            "description": "Own platform operations.",
            "department": "Operations",
            "status": "open",
            "hiring_manager_login": "manager-gamma",
        },
    )
    assert inactive_manager.status_code == 409
    assert inactive_manager.json()["detail"] == "hiring_manager_inactive"

    valid_response = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "Ops Engineer",
            "description": "Own platform operations.",
            "department": "Operations",
            "status": "open",
            "hiring_manager_login": "manager-alpha",
        },
    )
    assert valid_response.status_code == 200
    vacancy_id = valid_response.json()["vacancy_id"]

    patch_response = await api_client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        json={"hiring_manager_login": "manager-beta"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["hiring_manager_login"] == "manager-beta"

    clear_response = await api_client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        json={"hiring_manager_login": None},
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["hiring_manager_login"] is None
    assert clear_response.json()["hiring_manager_staff_id"] is None
