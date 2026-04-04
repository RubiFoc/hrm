"""Integration tests for employee directory APIs."""

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
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'employee_directory_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for employee directory integration tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
    )
    context_holder = {
        "context": AuthContext(
            subject_id=uuid4(),
            role="employee",
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
        yield app, context_holder, sqlite_database_url
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for ASGI in-process integration requests."""
    configured, _, _ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


def _seed_employee_profile(
    database_url: str,
    *,
    employee_id: str,
    staff_account_id: str | None,
    email: str,
    is_dismissed: bool,
    is_phone_visible: bool,
    is_email_visible: bool,
    is_birthday_visible: bool,
    birthday_day_month: str | None,
) -> None:
    """Insert one employee profile with required parent records."""
    vacancy_id = str(uuid4())
    candidate_id = str(uuid4())
    offer_id = str(uuid4())
    transition_id = str(uuid4())
    conversion_id = str(uuid4())
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                Vacancy(
                    vacancy_id=vacancy_id,
                    title="Platform Engineer",
                    description="Build the platform",
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
                    email=email,
                    phone="+375291234567",
                    location="Minsk",
                    current_title="Engineer",
                    extra_data={},
                )
            )
            session.add(
                Offer(
                    offer_id=offer_id,
                    vacancy_id=vacancy_id,
                    candidate_id=candidate_id,
                    status="accepted",
                    terms_summary=None,
                    proposed_start_date=date(2026, 4, 1),
                    expires_at=date(2026, 3, 20),
                    note=None,
                    sent_at=datetime(2026, 3, 10, 10, 30, tzinfo=UTC),
                    sent_by_staff_id=str(uuid4()),
                    decision_at=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
                    decision_note=None,
                    decision_recorded_by_staff_id=str(uuid4()),
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
                    changed_by_sub=str(uuid4()),
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
                        "email": email,
                        "phone": "+375291234567",
                        "location": "Minsk",
                        "current_title": "Engineer",
                        "extra_data": {},
                    },
                    offer_snapshot_json={
                        "status": "accepted",
                        "terms_summary": None,
                    },
                    converted_at=datetime(2026, 3, 10, 12, 5, tzinfo=UTC),
                    converted_by_staff_id=str(uuid4()),
                )
            )
            session.add(
                EmployeeProfile(
                    employee_id=employee_id,
                    hire_conversion_id=conversion_id,
                    vacancy_id=vacancy_id,
                    candidate_id=candidate_id,
                    first_name="Ada",
                    last_name="Lovelace",
                    email=email,
                    phone="+375291234567",
                    location="Minsk",
                    current_title="Engineer",
                    department="Engineering",
                    position_title="Platform Engineer",
                    manager="Grace Hopper",
                    birthday_day_month=birthday_day_month,
                    is_phone_visible=is_phone_visible,
                    is_email_visible=is_email_visible,
                    is_birthday_visible=is_birthday_visible,
                    is_dismissed=is_dismissed,
                    extra_data_json={},
                    offer_terms_summary=None,
                    start_date=date(2025, 1, 1),
                    staff_account_id=staff_account_id,
                    created_by_staff_id=str(uuid4()),
                    created_at=datetime(2026, 3, 10, 12, 10, tzinfo=UTC),
                    updated_at=datetime(2026, 3, 10, 12, 10, tzinfo=UTC),
                )
            )
            session.commit()
    finally:
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


async def test_employee_directory_list_redacts_private_fields(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify directory list redacts privacy fields for non-owner profiles."""
    _, context_holder, database_url = configured_app
    actor_subject = str(context_holder["context"].subject_id)
    owned_id = str(uuid4())
    other_id = str(uuid4())
    dismissed_id = str(uuid4())

    _seed_employee_profile(
        database_url,
        employee_id=owned_id,
        staff_account_id=actor_subject,
        email="owner@example.com",
        is_dismissed=False,
        is_phone_visible=False,
        is_email_visible=False,
        is_birthday_visible=False,
        birthday_day_month="03-12",
    )
    _seed_employee_profile(
        database_url,
        employee_id=other_id,
        staff_account_id=None,
        email="other@example.com",
        is_dismissed=False,
        is_phone_visible=False,
        is_email_visible=False,
        is_birthday_visible=False,
        birthday_day_month="05-10",
    )
    _seed_employee_profile(
        database_url,
        employee_id=dismissed_id,
        staff_account_id=None,
        email="dismissed@example.com",
        is_dismissed=True,
        is_phone_visible=True,
        is_email_visible=True,
        is_birthday_visible=True,
        birthday_day_month="01-01",
    )

    response = await api_client.get("/api/v1/employees/directory")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    items = {item["employee_id"]: item for item in payload["items"]}
    assert owned_id in items
    assert other_id in items
    assert dismissed_id not in items

    owner = items[owned_id]
    assert owner["phone"] == "+375291234567"
    assert owner["email"] == "owner@example.com"
    assert owner["birthday_day_month"] == "03-12"

    other = items[other_id]
    assert other["phone"] is None
    assert other["email"] is None
    assert other["birthday_day_month"] is None


async def test_dismissed_profile_read_is_hidden(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify dismissed profiles are hidden from directory profile reads."""
    _, context_holder, database_url = configured_app
    dismissed_id = str(uuid4())

    _seed_employee_profile(
        database_url,
        employee_id=dismissed_id,
        staff_account_id=None,
        email="dismissed@example.com",
        is_dismissed=True,
        is_phone_visible=True,
        is_email_visible=True,
        is_birthday_visible=True,
        birthday_day_month="01-01",
    )

    response = await api_client.get(f"/api/v1/employees/directory/{dismissed_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "employee_profile_dismissed"

    events = _load_events(database_url)
    failure_events = [
        event
        for event in events
        if event.action == "employee_directory:profile_read" and event.result == "failure"
    ]
    assert failure_events
    assert failure_events[-1].reason == "employee_profile_dismissed"
    assert failure_events[-1].resource_id == dismissed_id
