"""Integration tests for vacancy CRUD and pipeline transition APIs."""

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
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.interviews.models.feedback import InterviewFeedback
from hrm_backend.interviews.models.interview import Interview
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


def _seed_candidate(database_url: str, *, candidate_id: str, suffix: str) -> None:
    """Insert one candidate profile row directly for pipeline gate scenarios."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                CandidateProfile(
                    candidate_id=candidate_id,
                    owner_subject_id=f"candidate-{suffix}",
                    first_name="Gate",
                    last_name=suffix,
                    email=f"candidate-{suffix}@example.com",
                    phone=None,
                    location=None,
                    current_title=None,
                    extra_data={},
                )
            )
            session.commit()
    finally:
        engine.dispose()


def _insert_interview(
    database_url: str,
    *,
    vacancy_id: str,
    candidate_id: str,
    schedule_version: int,
    scheduled_start_at: datetime,
    scheduled_end_at: datetime,
    interviewer_staff_ids: list[str],
) -> str:
    """Persist one active interview row for a pipeline transition scenario."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            entity = Interview(
                vacancy_id=vacancy_id,
                candidate_id=candidate_id,
                status="awaiting_candidate_confirmation",
                calendar_sync_status="synced",
                schedule_version=schedule_version,
                scheduled_start_at=scheduled_start_at,
                scheduled_end_at=scheduled_end_at,
                timezone="UTC",
                location_kind="google_meet",
                location_details="https://meet.google.com/test-room",
                interviewer_staff_ids_json=interviewer_staff_ids,
                candidate_response_status="pending",
                created_by_staff_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                updated_by_staff_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                last_synced_at=scheduled_start_at,
            )
            session.add(entity)
            session.commit()
            session.refresh(entity)
            return entity.interview_id
    finally:
        engine.dispose()


def _insert_feedback(
    database_url: str,
    *,
    interview_id: str,
    schedule_version: int,
    interviewer_staff_id: str,
    requirements_match_score: int,
    communication_score: int,
    problem_solving_score: int,
    collaboration_score: int,
    recommendation: str,
    strengths_note: str,
    concerns_note: str,
    evidence_note: str,
) -> None:
    """Persist one structured feedback row for a fairness-gate scenario."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                InterviewFeedback(
                    interview_id=interview_id,
                    schedule_version=schedule_version,
                    interviewer_staff_id=interviewer_staff_id,
                    requirements_match_score=requirements_match_score,
                    communication_score=communication_score,
                    problem_solving_score=problem_solving_score,
                    collaboration_score=collaboration_score,
                    recommendation=recommendation,
                    strengths_note=strengths_note,
                    concerns_note=concerns_note,
                    evidence_note=evidence_note,
                )
            )
            session.commit()
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
    _, _, database_url, candidate_1_id, candidate_2_id = configured_app
    interviewer_a = "11111111-1111-4111-8111-111111111111"
    interviewer_b = "22222222-2222-4222-8222-222222222222"

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

    stages = ["applied", "screening", "shortlist", "interview", "offer", "hired"]
    for stage in stages[:4]:
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

    interview_id = _insert_interview(
        database_url,
        vacancy_id=vacancy_id,
        candidate_id=candidate_1_id,
        schedule_version=1,
        scheduled_start_at=datetime(2026, 3, 8, 10, 0, tzinfo=UTC),
        scheduled_end_at=datetime(2026, 3, 8, 11, 0, tzinfo=UTC),
        interviewer_staff_ids=[interviewer_a, interviewer_b],
    )
    _insert_feedback(
        database_url,
        interview_id=interview_id,
        schedule_version=1,
        interviewer_staff_id=interviewer_a,
        requirements_match_score=5,
        communication_score=4,
        problem_solving_score=5,
        collaboration_score=4,
        recommendation="strong_yes",
        strengths_note="Strong backend ownership.",
        concerns_note="No major concerns.",
        evidence_note="Clear design explanations.",
    )
    _insert_feedback(
        database_url,
        interview_id=interview_id,
        schedule_version=1,
        interviewer_staff_id=interviewer_b,
        requirements_match_score=4,
        communication_score=4,
        problem_solving_score=4,
        collaboration_score=5,
        recommendation="yes",
        strengths_note="Strong collaboration examples.",
        concerns_note="Minor ramp-up expected.",
        evidence_note="Grounded answers during the interview.",
    )

    offer_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": candidate_1_id,
            "to_stage": "offer",
            "reason": "progress",
        },
    )
    assert offer_transition.status_code == 200

    update_offer_response = await api_client.put(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_1_id}",
        json={
            "terms_summary": "Standard offer package for canonical pipeline test.",
        },
    )
    assert update_offer_response.status_code == 200

    send_offer_response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_1_id}/send"
    )
    assert send_offer_response.status_code == 200

    accept_offer_response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_1_id}/accept",
        json={"note": "Candidate accepted during canonical flow."},
    )
    assert accept_offer_response.status_code == 200

    hired_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": candidate_1_id,
            "to_stage": "hired",
            "reason": "progress",
        },
    )
    assert hired_transition.status_code == 200

    history_response = await api_client.get(
        "/api/v1/pipeline/transitions",
        params={
            "vacancy_id": vacancy_id,
            "candidate_id": candidate_1_id,
        },
    )
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert [item["to_stage"] for item in history_payload["items"]] == stages

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


async def test_interview_to_offer_feedback_gate_blocks_and_passes_by_reason_code(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify `interview -> offer` checks all feedback gate outcomes."""
    _, _, database_url, _, _ = configured_app
    interviewer_a = "11111111-1111-4111-8111-111111111111"
    interviewer_b = "22222222-2222-4222-8222-222222222222"

    create_response = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "Interview Fairness Gate",
            "description": "Offer transition fairness checks",
            "department": "Engineering",
            "status": "open",
        },
    )
    assert create_response.status_code == 200
    vacancy_id = create_response.json()["vacancy_id"]

    async def prepare_candidate(candidate_suffix: str) -> str:
        candidate_id = str(uuid5(NAMESPACE_URL, f"feedback-gate-{candidate_suffix}"))
        _seed_candidate(
            database_url,
            candidate_id=candidate_id,
            suffix=f"feedback-gate-{candidate_suffix}",
        )
        for stage in ["applied", "screening", "shortlist", "interview"]:
            transition = await api_client.post(
                "/api/v1/pipeline/transitions",
                json={
                    "vacancy_id": vacancy_id,
                    "candidate_id": candidate_id,
                    "to_stage": stage,
                    "reason": f"move_to_{stage}",
                },
            )
            assert transition.status_code == 200
        return candidate_id

    future_candidate_id = await prepare_candidate("future")
    future_interview_id = _insert_interview(
        database_url,
        vacancy_id=vacancy_id,
        candidate_id=future_candidate_id,
        schedule_version=1,
        scheduled_start_at=datetime(2026, 3, 11, 10, 0, tzinfo=UTC),
        scheduled_end_at=datetime(2026, 3, 11, 11, 0, tzinfo=UTC),
        interviewer_staff_ids=[interviewer_a],
    )
    _ = future_interview_id
    future_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": future_candidate_id,
            "to_stage": "offer",
            "reason": "future-window",
        },
    )
    assert future_transition.status_code == 409
    assert future_transition.json()["detail"] == "interview_feedback_window_not_open"

    missing_candidate_id = await prepare_candidate("missing")
    _insert_interview(
        database_url,
        vacancy_id=vacancy_id,
        candidate_id=missing_candidate_id,
        schedule_version=1,
        scheduled_start_at=datetime(2026, 3, 8, 10, 0, tzinfo=UTC),
        scheduled_end_at=datetime(2026, 3, 8, 11, 0, tzinfo=UTC),
        interviewer_staff_ids=[interviewer_a, interviewer_b],
    )
    missing_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": missing_candidate_id,
            "to_stage": "offer",
            "reason": "missing-feedback",
        },
    )
    assert missing_transition.status_code == 409
    assert missing_transition.json()["detail"] == "interview_feedback_missing"

    incomplete_candidate_id = await prepare_candidate("incomplete")
    incomplete_interview_id = _insert_interview(
        database_url,
        vacancy_id=vacancy_id,
        candidate_id=incomplete_candidate_id,
        schedule_version=1,
        scheduled_start_at=datetime(2026, 3, 8, 12, 0, tzinfo=UTC),
        scheduled_end_at=datetime(2026, 3, 8, 13, 0, tzinfo=UTC),
        interviewer_staff_ids=[interviewer_a],
    )
    _insert_feedback(
        database_url,
        interview_id=incomplete_interview_id,
        schedule_version=1,
        interviewer_staff_id=interviewer_a,
        requirements_match_score=5,
        communication_score=4,
        problem_solving_score=0,
        collaboration_score=5,
        recommendation="yes",
        strengths_note="Clear API experience.",
        concerns_note="Minor concerns remain.",
        evidence_note="Provided direct evidence.",
    )
    incomplete_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": incomplete_candidate_id,
            "to_stage": "offer",
            "reason": "incomplete-feedback",
        },
    )
    assert incomplete_transition.status_code == 409
    assert incomplete_transition.json()["detail"] == "interview_feedback_incomplete"

    stale_candidate_id = await prepare_candidate("stale")
    stale_interview_id = _insert_interview(
        database_url,
        vacancy_id=vacancy_id,
        candidate_id=stale_candidate_id,
        schedule_version=2,
        scheduled_start_at=datetime(2026, 3, 8, 14, 0, tzinfo=UTC),
        scheduled_end_at=datetime(2026, 3, 8, 15, 0, tzinfo=UTC),
        interviewer_staff_ids=[interviewer_a],
    )
    _insert_feedback(
        database_url,
        interview_id=stale_interview_id,
        schedule_version=1,
        interviewer_staff_id=interviewer_a,
        requirements_match_score=5,
        communication_score=5,
        problem_solving_score=4,
        collaboration_score=5,
        recommendation="strong_yes",
        strengths_note="Excellent ownership.",
        concerns_note="No major concerns.",
        evidence_note="Strong system design discussion.",
    )
    stale_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": stale_candidate_id,
            "to_stage": "offer",
            "reason": "stale-feedback",
        },
    )
    assert stale_transition.status_code == 409
    assert stale_transition.json()["detail"] == "interview_feedback_stale"

    success_candidate_id = await prepare_candidate("success")
    success_interview_id = _insert_interview(
        database_url,
        vacancy_id=vacancy_id,
        candidate_id=success_candidate_id,
        schedule_version=1,
        scheduled_start_at=datetime(2026, 3, 8, 16, 0, tzinfo=UTC),
        scheduled_end_at=datetime(2026, 3, 8, 17, 0, tzinfo=UTC),
        interviewer_staff_ids=[interviewer_a, interviewer_b],
    )
    _insert_feedback(
        database_url,
        interview_id=success_interview_id,
        schedule_version=1,
        interviewer_staff_id=interviewer_a,
        requirements_match_score=5,
        communication_score=4,
        problem_solving_score=5,
        collaboration_score=4,
        recommendation="strong_yes",
        strengths_note="Strong systems thinking.",
        concerns_note="No major concerns.",
        evidence_note="Explained architectural tradeoffs clearly.",
    )
    _insert_feedback(
        database_url,
        interview_id=success_interview_id,
        schedule_version=1,
        interviewer_staff_id=interviewer_b,
        requirements_match_score=4,
        communication_score=4,
        problem_solving_score=4,
        collaboration_score=5,
        recommendation="yes",
        strengths_note="Strong collaboration examples.",
        concerns_note="Small onboarding ramp expected.",
        evidence_note="Grounded feedback with candidate examples.",
    )
    success_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": success_candidate_id,
            "to_stage": "offer",
            "reason": "complete-panel",
        },
    )
    assert success_transition.status_code == 200
    assert success_transition.json()["to_stage"] == "offer"


async def test_offer_lifecycle_api_blocks_and_unblocks_pipeline_resolution(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify offer draft/send/accept lifecycle and `offer -> hired` gate behavior."""
    _, _, database_url, candidate_1_id, _ = configured_app
    interviewer_a = "11111111-1111-4111-8111-111111111111"

    create_response = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "Offer Lifecycle",
            "description": "Verify offer workflow",
            "department": "Engineering",
            "status": "open",
        },
    )
    assert create_response.status_code == 200
    vacancy_id = create_response.json()["vacancy_id"]

    for stage in ["applied", "screening", "shortlist", "interview"]:
        transition = await api_client.post(
            "/api/v1/pipeline/transitions",
            json={
                "vacancy_id": vacancy_id,
                "candidate_id": candidate_1_id,
                "to_stage": stage,
                "reason": f"move_to_{stage}",
            },
        )
        assert transition.status_code == 200

    interview_id = _insert_interview(
        database_url,
        vacancy_id=vacancy_id,
        candidate_id=candidate_1_id,
        schedule_version=1,
        scheduled_start_at=datetime(2026, 3, 8, 16, 0, tzinfo=UTC),
        scheduled_end_at=datetime(2026, 3, 8, 17, 0, tzinfo=UTC),
        interviewer_staff_ids=[interviewer_a],
    )
    _insert_feedback(
        database_url,
        interview_id=interview_id,
        schedule_version=1,
        interviewer_staff_id=interviewer_a,
        requirements_match_score=5,
        communication_score=4,
        problem_solving_score=5,
        collaboration_score=4,
        recommendation="strong_yes",
        strengths_note="Strong systems thinking.",
        concerns_note="No major concerns.",
        evidence_note="Grounded recommendation for offer.",
    )

    offer_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": candidate_1_id,
            "to_stage": "offer",
            "reason": "ready_for_offer",
        },
    )
    assert offer_transition.status_code == 200

    get_offer_response = await api_client.get(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_1_id}"
    )
    assert get_offer_response.status_code == 200
    assert get_offer_response.json()["status"] == "draft"
    assert get_offer_response.json()["terms_summary"] is None

    update_offer_response = await api_client.put(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_1_id}",
        json={
            "terms_summary": "Base salary 5000 BYN gross with probation bonus.",
            "proposed_start_date": "2026-04-01",
            "expires_at": "2026-03-20",
            "note": "Manual delivery via HR email.",
        },
    )
    assert update_offer_response.status_code == 200
    assert update_offer_response.json()["status"] == "draft"
    assert update_offer_response.json()["terms_summary"].startswith("Base salary")

    send_offer_response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_1_id}/send"
    )
    assert send_offer_response.status_code == 200
    assert send_offer_response.json()["status"] == "sent"
    assert send_offer_response.json()["sent_at"] is not None

    locked_update_response = await api_client.put(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_1_id}",
        json={
            "terms_summary": "Updated terms after sending.",
            "note": "Late edit should fail.",
        },
    )
    assert locked_update_response.status_code == 409
    assert locked_update_response.json()["detail"] == "offer_not_editable"

    blocked_hired_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": candidate_1_id,
            "to_stage": "hired",
            "reason": "skip_acceptance",
        },
    )
    assert blocked_hired_transition.status_code == 409
    assert blocked_hired_transition.json()["detail"] == "offer_not_accepted"

    accept_offer_response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_1_id}/accept",
        json={"note": "Candidate confirmed by phone."},
    )
    assert accept_offer_response.status_code == 200
    assert accept_offer_response.json()["status"] == "accepted"
    assert accept_offer_response.json()["decision_note"] == "Candidate confirmed by phone."

    hired_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": candidate_1_id,
            "to_stage": "hired",
            "reason": "accepted_offer",
        },
    )
    assert hired_transition.status_code == 200
    assert hired_transition.json()["to_stage"] == "hired"


async def test_offer_stage_and_decline_flow_return_stable_reason_codes(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify offer stage blockers, missing terms blocker, and decline-to-rejected flow."""
    _, _, database_url, _, candidate_2_id = configured_app
    interviewer_a = "11111111-1111-4111-8111-111111111111"

    create_response = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "Offer Decline",
            "description": "Verify decline flow",
            "department": "Engineering",
            "status": "open",
        },
    )
    assert create_response.status_code == 200
    vacancy_id = create_response.json()["vacancy_id"]

    blocked_offer_write = await api_client.put(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_2_id}",
        json={
            "terms_summary": "Offer should not be writable before pipeline reaches offer.",
        },
    )
    assert blocked_offer_write.status_code == 409
    assert blocked_offer_write.json()["detail"] == "offer_stage_not_active"

    for stage in ["applied", "screening", "shortlist", "interview"]:
        transition = await api_client.post(
            "/api/v1/pipeline/transitions",
            json={
                "vacancy_id": vacancy_id,
                "candidate_id": candidate_2_id,
                "to_stage": stage,
                "reason": f"move_to_{stage}",
            },
        )
        assert transition.status_code == 200

    interview_id = _insert_interview(
        database_url,
        vacancy_id=vacancy_id,
        candidate_id=candidate_2_id,
        schedule_version=1,
        scheduled_start_at=datetime(2026, 3, 8, 18, 0, tzinfo=UTC),
        scheduled_end_at=datetime(2026, 3, 8, 19, 0, tzinfo=UTC),
        interviewer_staff_ids=[interviewer_a],
    )
    _insert_feedback(
        database_url,
        interview_id=interview_id,
        schedule_version=1,
        interviewer_staff_id=interviewer_a,
        requirements_match_score=4,
        communication_score=4,
        problem_solving_score=4,
        collaboration_score=4,
        recommendation="yes",
        strengths_note="Ready for offer discussion.",
        concerns_note="Some onboarding ramp expected.",
        evidence_note="All required signals gathered.",
    )

    offer_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": candidate_2_id,
            "to_stage": "offer",
            "reason": "offer_stage_entered",
        },
    )
    assert offer_transition.status_code == 200

    blocked_send_response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_2_id}/send"
    )
    assert blocked_send_response.status_code == 409
    assert blocked_send_response.json()["detail"] == "offer_terms_missing"

    update_offer_response = await api_client.put(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_2_id}",
        json={
            "terms_summary": "Base salary 4200 BYN gross.",
            "note": "Offer prepared for decline scenario.",
        },
    )
    assert update_offer_response.status_code == 200

    send_offer_response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_2_id}/send"
    )
    assert send_offer_response.status_code == 200
    assert send_offer_response.json()["status"] == "sent"

    blocked_rejected_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": candidate_2_id,
            "to_stage": "rejected",
            "reason": "skip_decline_record",
        },
    )
    assert blocked_rejected_transition.status_code == 409
    assert blocked_rejected_transition.json()["detail"] == "offer_not_declined"

    decline_offer_response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/offers/{candidate_2_id}/decline",
        json={"note": "Candidate declined the compensation package."},
    )
    assert decline_offer_response.status_code == 200
    assert decline_offer_response.json()["status"] == "declined"

    rejected_transition = await api_client.post(
        "/api/v1/pipeline/transitions",
        json={
            "vacancy_id": vacancy_id,
            "candidate_id": candidate_2_id,
            "to_stage": "rejected",
            "reason": "declined_offer",
        },
    )
    assert rejected_transition.status_code == 200
    assert rejected_transition.json()["to_stage"] == "rejected"


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

    invalid_history_response = await api_client.get(
        "/api/v1/pipeline/transitions",
        params={
            "vacancy_id": vacancy_id,
            "candidate_id": "candidate-not-uuid",
        },
    )
    assert invalid_history_response.status_code == 422


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
    assert (
        schemas["InterviewFeedbackItemResponse"]["properties"]["feedback_id"]["format"]
        == "uuid"
    )
    assert (
        schemas["InterviewFeedbackItemResponse"]["properties"]["interview_id"]["format"]
        == "uuid"
    )
    assert (
        schemas["InterviewFeedbackItemResponse"]["properties"]["interviewer_staff_id"]["format"]
        == "uuid"
    )
    assert (
        schemas["InterviewFeedbackPanelSummaryResponse"]["properties"]["interview_id"]["format"]
        == "uuid"
    )

    vacancy_get_parameters = spec["paths"]["/api/v1/vacancies/{vacancy_id}"]["get"]["parameters"]
    candidate_get_parameters = spec["paths"]["/api/v1/candidates/{candidate_id}"]["get"][
        "parameters"
    ]
    candidate_analysis_get_parameters = spec["paths"][
        "/api/v1/candidates/{candidate_id}/cv/analysis"
    ]["get"]["parameters"]
    interview_feedback_get_parameters = spec["paths"][
        "/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/feedback"
    ]["get"]["parameters"]
    interview_feedback_put_parameters = spec["paths"][
        "/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/feedback/me"
    ]["put"]["parameters"]
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
    assert any(
        parameter["name"] == "vacancy_id"
        and parameter["schema"].get("format") == "uuid"
        for parameter in interview_feedback_get_parameters
    )
    assert any(
        parameter["name"] == "interview_id"
        and parameter["schema"].get("format") == "uuid"
        for parameter in interview_feedback_get_parameters
    )
    assert any(
        parameter["name"] == "vacancy_id"
        and parameter["schema"].get("format") == "uuid"
        for parameter in interview_feedback_put_parameters
    )
    assert any(
        parameter["name"] == "interview_id"
        and parameter["schema"].get("format") == "uuid"
        for parameter in interview_feedback_put_parameters
    )
