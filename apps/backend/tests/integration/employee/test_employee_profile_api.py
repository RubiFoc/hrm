"""Integration tests for employee profile bootstrap APIs."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.models.template import OnboardingTemplate, OnboardingTemplateItem
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'employee_profile_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for employee profile integration tests."""
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
    seeded = _seed_hire_conversion(sqlite_database_url)
    _seed_active_template(sqlite_database_url)
    try:
        yield app, context_holder, sqlite_database_url, seeded
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


def _seed_hire_conversion(database_url: str) -> dict[str, str]:
    """Insert one ready-state hire conversion with all required source rows."""
    vacancy_id = "11111111-1111-4111-8111-111111111111"
    candidate_id = "22222222-2222-4222-8222-222222222222"
    offer_id = "33333333-3333-4333-8333-333333333333"
    transition_id = "44444444-4444-4444-8444-444444444444"
    conversion_id = "55555555-5555-4555-8555-555555555555"
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                Vacancy(
                    vacancy_id=vacancy_id,
                    title="HRIS Engineer",
                    description="Build HR workflows",
                    department="Engineering",
                    status="open",
                )
            )
            session.add(
                CandidateProfile(
                    candidate_id=candidate_id,
                    owner_subject_id="candidate-owner",
                    first_name="Ada",
                    last_name="Lovelace",
                    email="ada@example.com",
                    phone="+375291234567",
                    location="Minsk",
                    current_title="Backend Engineer",
                    extra_data={"languages": ["ru", "en"]},
                )
            )
            session.add(
                Offer(
                    offer_id=offer_id,
                    vacancy_id=vacancy_id,
                    candidate_id=candidate_id,
                    status="accepted",
                    terms_summary="Base salary 5000 BYN gross.",
                    proposed_start_date=date(2026, 4, 1),
                    expires_at=date(2026, 3, 20),
                    note="Manual delivery by HR.",
                    sent_at=datetime(2026, 3, 10, 10, 30, tzinfo=UTC),
                    sent_by_staff_id="66666666-6666-4666-8666-666666666666",
                    decision_at=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
                    decision_note="Accepted by phone.",
                    decision_recorded_by_staff_id="77777777-7777-4777-8777-777777777777",
                )
            )
            session.add(
                PipelineTransition(
                    transition_id=transition_id,
                    vacancy_id=vacancy_id,
                    candidate_id=candidate_id,
                    from_stage="offer",
                    to_stage="hired",
                    reason="accepted_offer",
                    changed_by_sub="88888888-8888-4888-8888-888888888888",
                    changed_by_role="hr",
                    transitioned_at=datetime(2026, 3, 10, 12, 5, tzinfo=UTC),
                )
            )
            session.add(
                HireConversion(
                    conversion_id=conversion_id,
                    vacancy_id=vacancy_id,
                    candidate_id=candidate_id,
                    offer_id=offer_id,
                    hired_transition_id=transition_id,
                    status="ready",
                    candidate_snapshot_json={
                        "first_name": "Ada",
                        "last_name": "Lovelace",
                        "email": "ada@example.com",
                        "phone": "+375291234567",
                        "location": "Minsk",
                        "current_title": "Backend Engineer",
                        "extra_data": {"languages": ["ru", "en"]},
                    },
                    offer_snapshot_json={
                        "status": "accepted",
                        "terms_summary": "Base salary 5000 BYN gross.",
                        "proposed_start_date": "2026-04-01",
                        "expires_at": "2026-03-20",
                        "note": "Manual delivery by HR.",
                        "sent_at": "2026-03-10T10:30:00Z",
                        "sent_by_staff_id": "66666666-6666-4666-8666-666666666666",
                        "decision_at": "2026-03-10T12:00:00Z",
                        "decision_note": "Accepted by phone.",
                        "decision_recorded_by_staff_id": "77777777-7777-4777-8777-777777777777",
                    },
                    converted_at=datetime(2026, 3, 10, 12, 5, tzinfo=UTC),
                    converted_by_staff_id="88888888-8888-4888-8888-888888888888",
                )
            )
            session.commit()
    finally:
        engine.dispose()

    return {
        "vacancy_id": vacancy_id,
        "candidate_id": candidate_id,
        "conversion_id": conversion_id,
    }


def _seed_active_template(database_url: str) -> str:
    """Insert one active onboarding checklist template for task generation tests."""
    template_id = "99999999-9999-4999-8999-999999999999"
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                OnboardingTemplate(
                    template_id=template_id,
                    name="Default onboarding",
                    description="Core employee ramp-up checklist.",
                    is_active=True,
                    created_by_staff_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                )
            )
            session.add_all(
                [
                    OnboardingTemplateItem(
                        template_item_id="abababab-abab-4bab-8bab-abababababab",
                        template_id=template_id,
                        code="accounts",
                        title="Create accounts",
                        description="Provision required systems",
                        sort_order=20,
                        is_required=True,
                    ),
                    OnboardingTemplateItem(
                        template_item_id="cdcdcdcd-cdcd-4dcd-8dcd-cdcdcdcdcdcd",
                        template_id=template_id,
                        code="intro",
                        title="Team intro",
                        description=None,
                        sort_order=10,
                        is_required=False,
                    ),
                ]
            )
            session.commit()
    finally:
        engine.dispose()

    return template_id


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


def _load_employee_profiles(database_url: str) -> list[EmployeeProfile]:
    """Load ordered employee profile rows from database URL."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            return list(
                session.execute(
                    select(EmployeeProfile).order_by(
                        EmployeeProfile.created_at.asc(),
                        EmployeeProfile.employee_id.asc(),
                    )
                ).scalars()
            )
    finally:
        engine.dispose()


def _load_onboarding_runs(database_url: str) -> list[OnboardingRun]:
    """Load ordered onboarding rows from database URL."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            return list(
                session.execute(
                    select(OnboardingRun).order_by(
                        OnboardingRun.started_at.asc(),
                        OnboardingRun.onboarding_id.asc(),
                    )
                ).scalars()
            )
    finally:
        engine.dispose()


def _load_onboarding_tasks(database_url: str) -> list[OnboardingTask]:
    """Load ordered onboarding task rows from database URL."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            return list(
                session.execute(
                    select(OnboardingTask).order_by(
                        OnboardingTask.sort_order.asc(),
                        OnboardingTask.task_id.asc(),
                    )
                ).scalars()
            )
    finally:
        engine.dispose()


def _deactivate_all_templates(database_url: str) -> None:
    """Clear active flag from every onboarding template in the test database."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.query(OnboardingTemplate).update(
                {OnboardingTemplate.is_active: False},
                synchronize_session=False,
            )
            session.commit()
    finally:
        engine.dispose()


def _corrupt_candidate_snapshot(database_url: str, *, conversion_id: str) -> None:
    """Mutate one seeded hire conversion into an invalid snapshot payload."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            entity = session.get(HireConversion, conversion_id)
            assert entity is not None
            entity.candidate_snapshot_json = {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "extra_data": {},
            }
            session.add(entity)
            session.commit()
    finally:
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for employee integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_create_and_read_employee_profile_from_ready_hire_conversion(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify employee profile bootstrap uses the durable hire conversion as source of truth."""
    _, _, database_url, seeded = configured_app

    create_response = await api_client.post(
        "/api/v1/employees",
        json={
            "vacancy_id": seeded["vacancy_id"],
            "candidate_id": seeded["candidate_id"],
        },
    )
    assert create_response.status_code == 200
    payload = create_response.json()
    assert payload["hire_conversion_id"] == seeded["conversion_id"]
    assert payload["first_name"] == "Ada"
    assert payload["email"] == "ada@example.com"
    assert payload["offer_terms_summary"] == "Base salary 5000 BYN gross."
    assert payload["start_date"] == "2026-04-01"
    assert payload["extra_data"] == {"languages": ["ru", "en"]}
    assert payload["onboarding_status"] == "started"
    assert payload["onboarding_id"] is not None

    read_response = await api_client.get(f"/api/v1/employees/{payload['employee_id']}")
    assert read_response.status_code == 200
    assert read_response.json()["employee_id"] == payload["employee_id"]
    assert read_response.json()["onboarding_id"] == payload["onboarding_id"]
    assert read_response.json()["onboarding_status"] == "started"

    profiles = _load_employee_profiles(database_url)
    assert len(profiles) == 1
    assert profiles[0].hire_conversion_id == seeded["conversion_id"]

    onboarding_runs = _load_onboarding_runs(database_url)
    assert len(onboarding_runs) == 1
    assert onboarding_runs[0].employee_id == payload["employee_id"]
    assert onboarding_runs[0].hire_conversion_id == seeded["conversion_id"]
    assert onboarding_runs[0].status == "started"

    onboarding_tasks = _load_onboarding_tasks(database_url)
    assert len(onboarding_tasks) == 2
    assert [task.code for task in onboarding_tasks] == ["intro", "accounts"]
    assert all(task.onboarding_id == payload["onboarding_id"] for task in onboarding_tasks)
    assert all(task.status == "pending" for task in onboarding_tasks)

    events = _load_events(database_url)
    success_actions = [
        (event.action, event.result)
        for event in events
        if event.resource_type == "employee_profile"
    ]
    assert ("employee_profile:create", "success") in success_actions
    assert ("employee_profile:read", "success") in success_actions


async def test_employee_profile_api_reports_duplicate_missing_and_rbac_denials(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify duplicate bootstrap, missing handoff, and RBAC deny behavior."""
    _, context_holder, database_url, seeded = configured_app

    first_create = await api_client.post(
        "/api/v1/employees",
        json={
            "vacancy_id": seeded["vacancy_id"],
            "candidate_id": seeded["candidate_id"],
        },
    )
    assert first_create.status_code == 200
    employee_id = first_create.json()["employee_id"]

    duplicate_create = await api_client.post(
        "/api/v1/employees",
        json={
            "vacancy_id": seeded["vacancy_id"],
            "candidate_id": seeded["candidate_id"],
        },
    )
    assert duplicate_create.status_code == 409
    assert duplicate_create.json()["detail"] == "employee_profile_already_exists"

    missing_create = await api_client.post(
        "/api/v1/employees",
        json={
            "vacancy_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "candidate_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        },
    )
    assert missing_create.status_code == 404
    assert missing_create.json()["detail"] == "hire_conversion_not_found"

    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    forbidden_get = await api_client.get(f"/api/v1/employees/{employee_id}")
    assert forbidden_get.status_code == 403

    onboarding_runs = _load_onboarding_runs(database_url)
    assert len(onboarding_runs) == 1
    assert onboarding_runs[0].employee_id == employee_id
    assert len(_load_onboarding_tasks(database_url)) == 2

    events = _load_events(database_url)
    denied_events = [
        event
        for event in events
        if event.action == "employee_profile:read" and event.result == "denied"
    ]
    assert len(denied_events) == 1
    assert denied_events[0].actor_role == "manager"


async def test_employee_profile_create_returns_422_for_invalid_hire_conversion_snapshot(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify malformed durable handoff data fails closed at the employee API boundary."""
    _, _, database_url, seeded = configured_app
    _corrupt_candidate_snapshot(database_url, conversion_id=seeded["conversion_id"])

    response = await api_client.post(
        "/api/v1/employees",
        json={
            "vacancy_id": seeded["vacancy_id"],
            "candidate_id": seeded["candidate_id"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "hire_conversion_invalid"
    assert _load_employee_profiles(database_url) == []
    assert _load_onboarding_runs(database_url) == []
    assert _load_onboarding_tasks(database_url) == []


async def test_employee_profile_create_returns_422_when_active_onboarding_template_is_missing(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify bootstrap fails closed when onboarding task materialization has no active template."""
    _, _, database_url, seeded = configured_app
    _deactivate_all_templates(database_url)

    response = await api_client.post(
        "/api/v1/employees",
        json={
            "vacancy_id": seeded["vacancy_id"],
            "candidate_id": seeded["candidate_id"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "onboarding_template_not_configured"
    assert _load_employee_profiles(database_url) == []
    assert _load_onboarding_runs(database_url) == []
    assert _load_onboarding_tasks(database_url) == []
