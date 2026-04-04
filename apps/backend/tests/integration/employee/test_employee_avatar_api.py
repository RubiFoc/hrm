"""Integration tests for employee avatar APIs."""

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
from hrm_backend.employee.dependencies.employee import get_employee_avatar_storage
from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy

pytestmark = pytest.mark.anyio


class InMemoryAvatarStorage:
    """In-memory avatar storage stub for integration tests."""

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
        self._store[object_key] = data

    def get_object(self, *, object_key: str) -> bytes:
        return self._store[object_key]

    def remove_object(self, *, object_key: str) -> None:
        self._store.pop(object_key, None)


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'employee_avatar_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for employee avatar integration tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
    )
    storage = InMemoryAvatarStorage()
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

    def _get_storage_override() -> InMemoryAvatarStorage:
        return storage

    app.dependency_overrides[get_settings] = _get_settings_override
    app.dependency_overrides[get_current_auth_context] = _get_auth_context_override
    app.dependency_overrides[get_employee_avatar_storage] = _get_storage_override

    engine = create_engine(sqlite_database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        yield app, context_holder, sqlite_database_url
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_employee_avatar_storage, None)
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
    staff_account_id: str,
    email: str,
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
                    birthday_day_month=None,
                    is_phone_visible=False,
                    is_email_visible=False,
                    is_birthday_visible=False,
                    is_dismissed=False,
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


async def test_employee_avatar_upload_read_delete(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify upload, read, and delete flows for employee avatars."""
    _, context_holder, database_url = configured_app
    employee_id = str(uuid4())
    actor_subject = str(context_holder["context"].subject_id)

    _seed_employee_profile(
        database_url,
        employee_id=employee_id,
        staff_account_id=actor_subject,
        email="employee@example.com",
    )

    upload_response = await api_client.post(
        "/api/v1/employees/me/avatar",
        files={"file": ("avatar.png", b"pngdata", "image/png")},
    )
    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["employee_id"] == employee_id
    assert payload["mime_type"] == "image/png"

    read_response = await api_client.get(f"/api/v1/employees/{employee_id}/avatar")
    assert read_response.status_code == 200
    assert read_response.headers["content-type"] == "image/png"
    assert read_response.content == b"pngdata"

    delete_response = await api_client.delete("/api/v1/employees/me/avatar")
    assert delete_response.status_code == 200
    assert delete_response.json()["employee_id"] == employee_id

    missing_response = await api_client.get(f"/api/v1/employees/{employee_id}/avatar")
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "employee_avatar_not_found"

    events = _load_events(database_url)
    actions = [event.action for event in events if event.resource_type == "employee_avatar"]
    assert "employee_avatar:upload" in actions
    assert "employee_avatar:read" in actions
    assert "employee_avatar:delete" in actions


async def test_employee_avatar_rejects_invalid_mime_type(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify avatar upload rejects unsupported MIME types."""
    _, context_holder, database_url = configured_app
    employee_id = str(uuid4())
    actor_subject = str(context_holder["context"].subject_id)

    _seed_employee_profile(
        database_url,
        employee_id=employee_id,
        staff_account_id=actor_subject,
        email="employee@example.com",
    )

    response = await api_client.post(
        "/api/v1/employees/me/avatar",
        files={"file": ("avatar.bmp", b"bmpdata", "image/bmp")},
    )
    assert response.status_code == 415
    assert response.json()["detail"] == "avatar_mime_unsupported"

    events = _load_events(database_url)
    failures = [
        event
        for event in events
        if event.action == "employee_avatar:upload" and event.result == "failure"
    ]
    assert failures
    assert failures[-1].reason == "avatar_mime_unsupported"
