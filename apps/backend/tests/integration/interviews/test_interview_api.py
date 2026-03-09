"""Integration tests for interview scheduling APIs, public registration, and sync states."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.audit.dao.audit_event_dao import AuditEventDAO
from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.interviews.dao.calendar_binding_dao import InterviewCalendarBindingDAO
from hrm_backend.interviews.dao.interview_dao import InterviewDAO
from hrm_backend.interviews.dependencies.interviews import get_interview_calendar_adapter
from hrm_backend.interviews.infra.google_calendar.adapter import (
    CalendarBindingSyncPayload,
    CalendarSyncResult,
)
from hrm_backend.interviews.models.interview import Interview
from hrm_backend.interviews.services.interview_sync_worker_service import InterviewSyncWorkerService
from hrm_backend.interviews.utils.tokens import InterviewTokenManager
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO

pytestmark = pytest.mark.anyio

INTERVIEWER_A = "11111111-1111-4111-8111-111111111111"
INTERVIEWER_B = "22222222-2222-4222-8222-222222222222"


@dataclass
class _FakeCalendarAdapter:
    """Deterministic shared-calendar adapter for integration tests."""

    configured: bool = True
    staff_calendar_map: dict[str, str] = field(
        default_factory=lambda: {
            INTERVIEWER_A: "alpha@example.com",
            INTERVIEWER_B: "beta@example.com",
        }
    )
    sync_mode: str = "synced"
    cancel_mode: str = "synced"
    sync_exception: Exception | None = None
    cancel_exception: Exception | None = None
    on_sync: Callable[[Interview], None] | None = None
    sync_calls: list[dict[str, object]] = field(default_factory=list)
    cancel_calls: list[dict[str, object]] = field(default_factory=list)

    def is_configured(self) -> bool:
        """Return whether adapter is available for sync."""
        return self.configured

    def ensure_ready_for_interviewers(self, interviewer_staff_ids: list[str]) -> dict[str, str]:
        """Validate calendar mappings for requested interviewer list."""
        if not self.configured:
            raise RuntimeError("calendar_not_configured")
        missing = [
            staff_id
            for staff_id in interviewer_staff_ids
            if staff_id not in self.staff_calendar_map
        ]
        if missing:
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail="interviewer_calendar_not_configured")
        return {staff_id: self.staff_calendar_map[staff_id] for staff_id in interviewer_staff_ids}

    def sync_schedule(
        self,
        *,
        interview: Interview,
        vacancy_title: str,
        candidate_display_name: str,
        existing_bindings,
    ) -> CalendarSyncResult:
        """Return deterministic sync outcomes for the worker flow."""
        self.sync_calls.append(
            {
                "interview_id": interview.interview_id,
                "vacancy_title": vacancy_title,
                "candidate_display_name": candidate_display_name,
                "existing_bindings_count": len(existing_bindings),
            }
        )
        if self.on_sync is not None:
            self.on_sync(interview)
        if self.sync_exception is not None:
            raise self.sync_exception
        if self.sync_mode == "conflict":
            return CalendarSyncResult(
                status="conflict",
                bindings=[],
                reason_code="calendar_conflict",
                error_detail="conflicting_event_id=test-event",
            )
        if self.sync_mode == "failed":
            return CalendarSyncResult(
                status="failed",
                bindings=[],
                reason_code="calendar_sync_failed",
                error_detail="simulated_failure",
            )
        sorted_staff_ids = sorted(interview.interviewer_staff_ids_json)
        bindings = [
            CalendarBindingSyncPayload(
                interviewer_staff_id=staff_id,
                calendar_id=self.staff_calendar_map[staff_id],
                calendar_event_id=f"evt-{staff_id[-4:]}-v{interview.schedule_version}",
            )
            for staff_id in sorted_staff_ids
        ]
        location_details = (
            "https://meet.google.com/test-room"
            if interview.location_kind == "google_meet"
            else interview.location_details
        )
        return CalendarSyncResult(
            status="synced",
            bindings=bindings,
            primary_calendar_event_id=bindings[0].calendar_event_id,
            resolved_location_details=location_details,
        )

    def cancel_schedule(self, *, interview: Interview, existing_bindings) -> CalendarSyncResult:
        """Return deterministic cancellation outcomes for the worker flow."""
        self.cancel_calls.append(
            {
                "interview_id": interview.interview_id,
                "existing_bindings_count": len(existing_bindings),
            }
        )
        if self.cancel_exception is not None:
            raise self.cancel_exception
        if self.cancel_mode == "failed":
            return CalendarSyncResult(
                status="failed",
                bindings=[],
                reason_code="calendar_sync_failed",
                error_detail="simulated_cancel_failure",
            )
        return CalendarSyncResult(status="synced", bindings=[])


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite database URL for interview integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'interviews.db'}"


@pytest.fixture()
def configured_app(
    sqlite_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Configure the ASGI app with SQLite storage, fake auth, and fake calendar adapter."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
        google_calendar_enabled=True,
        public_frontend_base_url="https://frontend.example",
        interview_public_token_secret="interview-public-secret",
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
    fake_adapter = _FakeCalendarAdapter()

    def _get_settings_override() -> AppSettings:
        return settings

    def _get_auth_context_override() -> AuthContext:
        return context_holder["context"]

    def _get_fake_calendar_adapter() -> _FakeCalendarAdapter:
        return fake_adapter

    app.dependency_overrides[get_settings] = _get_settings_override
    app.dependency_overrides[get_current_auth_context] = _get_auth_context_override
    app.dependency_overrides[get_interview_calendar_adapter] = _get_fake_calendar_adapter

    monkeypatch.setattr(
        "hrm_backend.interviews.services.interview_service.enqueue_interview_sync",
        lambda **_: None,
    )

    engine = create_engine(sqlite_database_url, future=True)
    Base.metadata.create_all(engine)

    try:
        yield {
            "app": app,
            "engine": engine,
            "settings": settings,
            "context_holder": context_holder,
            "adapter": fake_adapter,
            "database_url": sqlite_database_url,
        }
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_interview_calendar_adapter, None)
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async client over the configured in-process ASGI app."""
    async with AsyncClient(
        transport=ASGITransport(app=configured_app["app"]),
        base_url="http://testserver",
    ) as client:
        yield client


def _seed_candidate(engine, *, candidate_id: str, suffix: str) -> None:
    """Insert one candidate profile row for interview flow tests."""
    with Session(engine) as session:
        session.add(
            CandidateProfile(
                candidate_id=candidate_id,
                owner_subject_id=f"public-{suffix}",
                first_name="Jane",
                last_name=f"Candidate-{suffix}",
                email=f"candidate-{suffix}@example.com",
                phone="+375291112233",
                location="Minsk",
                current_title="Engineer",
                extra_data={},
            )
        )
        session.commit()


async def _create_vacancy(api_client: AsyncClient, *, title_suffix: str) -> str:
    """Create one vacancy through the HR API and return its UUID."""
    response = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": f"Backend Engineer {title_suffix}",
            "description": "Build interview scheduling APIs",
            "department": "Engineering",
            "status": "open",
        },
    )
    assert response.status_code == 200
    return response.json()["vacancy_id"]


async def _append_transition(
    api_client: AsyncClient,
    *,
    vacancy_id: str,
    candidate_id: str,
    to_stage: str,
) -> None:
    """Append canonical pipeline transitions until the requested stage is reached."""
    canonical_stages = ["applied", "screening", "shortlist", "interview", "offer", "hired"]
    target_index = canonical_stages.index(to_stage)
    for stage in canonical_stages[: target_index + 1]:
        response = await api_client.post(
            "/api/v1/pipeline/transitions",
            json={
                "vacancy_id": vacancy_id,
                "candidate_id": candidate_id,
                "to_stage": stage,
                "reason": f"move_to_{stage}",
            },
        )
        assert response.status_code == 200


async def _create_interview(
    api_client: AsyncClient,
    *,
    vacancy_id: str,
    candidate_id: str,
    interviewer_staff_ids: list[str] | None = None,
    scheduled_start_local: str = "2026-03-12T10:00:00",
    scheduled_end_local: str = "2026-03-12T11:00:00",
    location_kind: str = "google_meet",
    location_details: str | None = None,
) -> dict[str, object]:
    """Create one interview through the HR API and return response JSON."""
    response = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/interviews",
        json={
            "candidate_id": candidate_id,
            "scheduled_start_local": scheduled_start_local,
            "scheduled_end_local": scheduled_end_local,
            "timezone": "Europe/Minsk",
            "location_kind": location_kind,
            "location_details": location_details,
            "interviewer_staff_ids": interviewer_staff_ids or [INTERVIEWER_A, INTERVIEWER_B],
        },
    )
    assert response.status_code == 200
    return response.json()


def _extract_token(invite_url: str) -> str:
    """Extract public interview token from invite URL."""
    parsed = urlparse(invite_url)
    return parse_qs(parsed.query)["interviewToken"][0]


def _build_worker(configured_app) -> InterviewSyncWorkerService:
    """Build DB-backed worker service that reuses the configured fake adapter."""
    session = Session(configured_app["engine"])
    return InterviewSyncWorkerService(
        settings=configured_app["settings"],
        interview_dao=InterviewDAO(session=session),
        binding_dao=InterviewCalendarBindingDAO(session=session),
        vacancy_dao=VacancyDAO(session=session),
        candidate_profile_dao=CandidateProfileDAO(session=session),
        transition_dao=PipelineTransitionDAO(session=session),
        calendar_adapter=configured_app["adapter"],
        token_manager=InterviewTokenManager(
            secret=configured_app["settings"].interview_public_token_secret
            or configured_app["settings"].jwt_secret,
        ),
        audit_service=AuditService(dao=AuditEventDAO(session=session)),
    )


def _run_worker(configured_app, *, interview_id: str) -> str:
    """Run one worker iteration and ensure the shared SQLAlchemy session closes."""
    worker = _build_worker(configured_app)
    try:
        return worker.process_interview_by_id(interview_id=interview_id).status
    finally:
        worker._interview_dao._session.close()  # noqa: SLF001


def _load_interview(engine, interview_id: str) -> Interview:
    """Load one interview row directly from the database."""
    with Session(engine) as session:
        entity = session.get(Interview, interview_id)
        assert entity is not None
        return entity


def _load_audit_events(engine) -> list[AuditEvent]:
    """Load ordered audit events for assertions."""
    with Session(engine) as session:
        return list(
            session.execute(
                select(AuditEvent).order_by(AuditEvent.occurred_at, AuditEvent.event_id)
            ).scalars()
        )


async def test_create_requires_shortlist_and_exposes_hr_interview_reads(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify HR create/list/get endpoints follow the pipeline gate and queued contract."""
    candidate_id = str(UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"))
    _seed_candidate(configured_app["engine"], candidate_id=candidate_id, suffix="read")
    vacancy_id = await _create_vacancy(api_client, title_suffix="read")

    forbidden_create = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/interviews",
        json={
            "candidate_id": candidate_id,
            "scheduled_start_local": "2026-03-12T10:00:00",
            "scheduled_end_local": "2026-03-12T11:00:00",
            "timezone": "Europe/Minsk",
            "location_kind": "google_meet",
            "location_details": None,
            "interviewer_staff_ids": [INTERVIEWER_A],
        },
    )
    assert forbidden_create.status_code == 422
    assert forbidden_create.json()["detail"] == "invalid_pipeline_stage"

    await _append_transition(
        api_client,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        to_stage="shortlist",
    )
    created = await _create_interview(
        api_client,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        interviewer_staff_ids=[INTERVIEWER_A],
    )

    assert created["status"] == "pending_sync"
    assert created["calendar_sync_status"] == "queued"
    assert created["candidate_invite_url"] is None

    listed = await api_client.get(
        f"/api/v1/vacancies/{vacancy_id}/interviews",
        params={"candidate_id": candidate_id},
    )
    assert listed.status_code == 200
    assert listed.json()["items"][0]["interview_id"] == created["interview_id"]

    fetched = await api_client.get(
        f"/api/v1/vacancies/{vacancy_id}/interviews/{created['interview_id']}"
    )
    assert fetched.status_code == 200
    assert fetched.json()["interviewer_staff_ids"] == [INTERVIEWER_A]


async def test_duplicate_active_interview_returns_409(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify one-active-interview rule rejects duplicate creates for the same pair."""
    candidate_id = str(UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"))
    _seed_candidate(configured_app["engine"], candidate_id=candidate_id, suffix="dup")
    vacancy_id = await _create_vacancy(api_client, title_suffix="dup")
    await _append_transition(
        api_client,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        to_stage="shortlist",
    )

    await _create_interview(api_client, vacancy_id=vacancy_id, candidate_id=candidate_id)
    duplicate = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/interviews",
        json={
            "candidate_id": candidate_id,
            "scheduled_start_local": "2026-03-13T10:00:00",
            "scheduled_end_local": "2026-03-13T11:00:00",
            "timezone": "Europe/Minsk",
            "location_kind": "onsite",
            "location_details": "Office 1",
            "interviewer_staff_ids": [INTERVIEWER_A],
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "active_interview_already_exists"


async def test_hr_reschedule_cancel_and_resend_invite_flow(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify HR invite lifecycle, reschedule invalidation, and cancellation."""
    candidate_id = str(UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"))
    _seed_candidate(configured_app["engine"], candidate_id=candidate_id, suffix="hr")
    vacancy_id = await _create_vacancy(api_client, title_suffix="hr")
    await _append_transition(
        api_client,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        to_stage="shortlist",
    )
    created = await _create_interview(api_client, vacancy_id=vacancy_id, candidate_id=candidate_id)

    assert _run_worker(configured_app, interview_id=created["interview_id"]) == "synced"

    fetched = await api_client.get(
        f"/api/v1/vacancies/{vacancy_id}/interviews/{created['interview_id']}"
    )
    assert fetched.status_code == 200
    initial_payload = fetched.json()
    assert initial_payload["status"] == "awaiting_candidate_confirmation"
    assert initial_payload["calendar_sync_status"] == "synced"
    assert initial_payload["candidate_invite_url"].startswith("https://frontend.example/candidate?")
    original_token = _extract_token(initial_payload["candidate_invite_url"])

    resent = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/interviews/{created['interview_id']}/resend-invite"
    )
    assert resent.status_code == 200
    resent_payload = resent.json()
    resent_token = _extract_token(resent_payload["candidate_invite_url"])
    assert resent_token != original_token

    old_public = await api_client.get(f"/api/v1/public/interview-registrations/{original_token}")
    assert old_public.status_code == 404
    assert old_public.json()["detail"] == "interview_registration_not_found"

    rescheduled = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/interviews/{created['interview_id']}/reschedule",
        json={
            "scheduled_start_local": "2026-03-14T13:00:00",
            "scheduled_end_local": "2026-03-14T14:00:00",
            "timezone": "Europe/Minsk",
            "location_kind": "onsite",
            "location_details": "Minsk office",
            "interviewer_staff_ids": [INTERVIEWER_A, INTERVIEWER_B],
        },
    )
    assert rescheduled.status_code == 200
    assert rescheduled.json()["schedule_version"] == 2
    assert rescheduled.json()["calendar_sync_status"] == "queued"
    assert rescheduled.json()["candidate_invite_url"] is None

    assert _run_worker(configured_app, interview_id=created["interview_id"]) == "synced"

    cancelled = await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/interviews/{created['interview_id']}/cancel",
        json={"cancel_reason_code": "cancelled_by_staff"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["calendar_sync_status"] == "queued"

    assert _run_worker(configured_app, interview_id=created["interview_id"]) == "synced"

    final_row = _load_interview(configured_app["engine"], created["interview_id"])
    assert final_row.calendar_event_id is None
    assert final_row.candidate_token_hash is None


async def test_public_confirm_reschedule_decline_and_expired_token(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify public token endpoints cover confirm, reschedule request, decline, and 410 expiry."""
    confirm_candidate_id = str(UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"))
    _seed_candidate(configured_app["engine"], candidate_id=confirm_candidate_id, suffix="public-1")
    confirm_vacancy_id = await _create_vacancy(api_client, title_suffix="public-1")
    await _append_transition(
        api_client,
        vacancy_id=confirm_vacancy_id,
        candidate_id=confirm_candidate_id,
        to_stage="shortlist",
    )
    confirm_created = await _create_interview(
        api_client,
        vacancy_id=confirm_vacancy_id,
        candidate_id=confirm_candidate_id,
    )
    assert _run_worker(configured_app, interview_id=confirm_created["interview_id"]) == "synced"

    confirmed_fetch = await api_client.get(
        f"/api/v1/vacancies/{confirm_vacancy_id}/interviews/{confirm_created['interview_id']}"
    )
    confirm_token = _extract_token(confirmed_fetch.json()["candidate_invite_url"])

    public_get = await api_client.get(f"/api/v1/public/interview-registrations/{confirm_token}")
    assert public_get.status_code == 200
    assert public_get.json()["candidate_response_status"] == "pending"

    confirmed = await api_client.post(
        f"/api/v1/public/interview-registrations/{confirm_token}/confirm"
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    requested = await api_client.post(
        f"/api/v1/public/interview-registrations/{confirm_token}/request-reschedule",
        json={"note": "Need a later slot"},
    )
    assert requested.status_code == 200
    assert requested.json()["status"] == "reschedule_requested"
    assert requested.json()["candidate_response_note"] == "Need a later slot"

    decline_candidate_id = str(UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"))
    _seed_candidate(configured_app["engine"], candidate_id=decline_candidate_id, suffix="public-2")
    decline_vacancy_id = await _create_vacancy(api_client, title_suffix="public-2")
    await _append_transition(
        api_client,
        vacancy_id=decline_vacancy_id,
        candidate_id=decline_candidate_id,
        to_stage="shortlist",
    )
    decline_created = await _create_interview(
        api_client,
        vacancy_id=decline_vacancy_id,
        candidate_id=decline_candidate_id,
    )
    assert _run_worker(configured_app, interview_id=decline_created["interview_id"]) == "synced"

    decline_fetch = await api_client.get(
        f"/api/v1/vacancies/{decline_vacancy_id}/interviews/{decline_created['interview_id']}"
    )
    decline_token = _extract_token(decline_fetch.json()["candidate_invite_url"])
    declined = await api_client.post(
        f"/api/v1/public/interview-registrations/{decline_token}/cancel",
        json={"note": "I am no longer available"},
    )
    assert declined.status_code == 200
    assert declined.json()["status"] == "cancelled"
    assert declined.json()["candidate_response_status"] == "declined"
    assert declined.json()["calendar_sync_status"] == "queued"

    assert _run_worker(configured_app, interview_id=decline_created["interview_id"]) == "synced"

    expired_candidate_id = str(UUID("ffffffff-ffff-4fff-8fff-ffffffffffff"))
    _seed_candidate(configured_app["engine"], candidate_id=expired_candidate_id, suffix="public-3")
    expired_vacancy_id = await _create_vacancy(api_client, title_suffix="public-3")
    await _append_transition(
        api_client,
        vacancy_id=expired_vacancy_id,
        candidate_id=expired_candidate_id,
        to_stage="shortlist",
    )
    expired_created = await _create_interview(
        api_client,
        vacancy_id=expired_vacancy_id,
        candidate_id=expired_candidate_id,
    )
    assert _run_worker(configured_app, interview_id=expired_created["interview_id"]) == "synced"

    expired_fetch = await api_client.get(
        f"/api/v1/vacancies/{expired_vacancy_id}/interviews/{expired_created['interview_id']}"
    )
    expired_token = _extract_token(expired_fetch.json()["candidate_invite_url"])
    with Session(configured_app["engine"]) as session:
        entity = session.get(Interview, expired_created["interview_id"])
        assert entity is not None
        entity.candidate_token_expires_at = entity.created_at.replace(year=2025)
        session.add(entity)
        session.commit()

    expired_response = await api_client.get(
        f"/api/v1/public/interview-registrations/{expired_token}"
    )
    assert expired_response.status_code == 410
    assert expired_response.json()["detail"] == "interview_registration_token_expired"


async def test_interview_sync_state_machine_and_pipeline_append(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify queued/running/synced/conflict/failed states and shortlist->interview append."""
    running_observation: dict[str, str] = {}

    def _capture_running_state(interview: Interview) -> None:
        with Session(configured_app["engine"]) as session:
            current = session.get(Interview, interview.interview_id)
            assert current is not None
            running_observation["status"] = current.calendar_sync_status

    configured_app["adapter"].on_sync = _capture_running_state

    synced_candidate_id = str(UUID("12121212-1212-4212-8212-121212121212"))
    _seed_candidate(configured_app["engine"], candidate_id=synced_candidate_id, suffix="sync-ok")
    synced_vacancy_id = await _create_vacancy(api_client, title_suffix="sync-ok")
    await _append_transition(
        api_client,
        vacancy_id=synced_vacancy_id,
        candidate_id=synced_candidate_id,
        to_stage="shortlist",
    )
    synced_created = await _create_interview(
        api_client,
        vacancy_id=synced_vacancy_id,
        candidate_id=synced_candidate_id,
    )
    assert (
        _load_interview(
            configured_app["engine"],
            synced_created["interview_id"],
        ).calendar_sync_status
        == "queued"
    )

    assert _run_worker(configured_app, interview_id=synced_created["interview_id"]) == "synced"
    assert running_observation["status"] == "running"
    synced_row = _load_interview(configured_app["engine"], synced_created["interview_id"])
    assert synced_row.calendar_sync_status == "synced"
    assert synced_row.status == "awaiting_candidate_confirmation"
    with Session(configured_app["engine"]) as session:
        last_transition = PipelineTransitionDAO(session=session).get_last_transition(
            vacancy_id=synced_vacancy_id,
            candidate_id=synced_candidate_id,
        )
        assert last_transition is not None
        assert last_transition.to_stage == "interview"

    conflict_candidate_id = str(UUID("34343434-3434-4343-8343-343434343434"))
    _seed_candidate(
        configured_app["engine"],
        candidate_id=conflict_candidate_id,
        suffix="sync-conflict",
    )
    conflict_vacancy_id = await _create_vacancy(api_client, title_suffix="sync-conflict")
    await _append_transition(
        api_client,
        vacancy_id=conflict_vacancy_id,
        candidate_id=conflict_candidate_id,
        to_stage="shortlist",
    )
    conflict_created = await _create_interview(
        api_client,
        vacancy_id=conflict_vacancy_id,
        candidate_id=conflict_candidate_id,
        interviewer_staff_ids=[INTERVIEWER_A],
    )
    configured_app["adapter"].sync_mode = "conflict"
    assert _run_worker(configured_app, interview_id=conflict_created["interview_id"]) == "conflict"
    conflict_row = _load_interview(configured_app["engine"], conflict_created["interview_id"])
    assert conflict_row.calendar_sync_status == "conflict"
    assert conflict_row.status == "reschedule_requested"

    failed_candidate_id = str(UUID("56565656-5656-4565-8565-565656565656"))
    _seed_candidate(
        configured_app["engine"],
        candidate_id=failed_candidate_id,
        suffix="sync-failed",
    )
    failed_vacancy_id = await _create_vacancy(api_client, title_suffix="sync-failed")
    await _append_transition(
        api_client,
        vacancy_id=failed_vacancy_id,
        candidate_id=failed_candidate_id,
        to_stage="shortlist",
    )
    failed_created = await _create_interview(
        api_client,
        vacancy_id=failed_vacancy_id,
        candidate_id=failed_candidate_id,
        interviewer_staff_ids=[INTERVIEWER_A],
    )
    configured_app["adapter"].sync_mode = "synced"
    configured_app["adapter"].sync_exception = RuntimeError("calendar backend down")
    assert _run_worker(configured_app, interview_id=failed_created["interview_id"]) == "failed"
    failed_row = _load_interview(configured_app["engine"], failed_created["interview_id"])
    assert failed_row.calendar_sync_status == "failed"
    assert failed_row.calendar_sync_reason_code == "calendar_sync_failed"

    events = _load_audit_events(configured_app["engine"])
    sync_events = [event for event in events if event.action == "interview:sync"]
    assert any(event.result == "success" for event in sync_events)
    assert any(event.reason == "calendar_conflict" for event in sync_events)
    assert any(event.reason == "calendar_sync_failed" for event in sync_events)
