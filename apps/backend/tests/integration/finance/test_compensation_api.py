"""Integration tests for compensation control APIs."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.models.vacancy import Vacancy

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for compensation API tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'compensation_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for compensation API tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
        compensation_raise_manager_quorum=2,
    )
    context_holder = {
        "context": AuthContext(
            subject_id=uuid4(),
            role="manager",
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
    _seed_compensation_fixtures(sqlite_database_url)
    try:
        yield app, context_holder, sqlite_database_url
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


def _seed_compensation_fixtures(database_url: str) -> dict[str, str]:
    """Insert vacancy and employee fixtures for compensation API tests."""
    manager_staff_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    vacancy_id = "11111111-1111-4111-8111-111111111111"
    employee_id = "22222222-2222-4222-8222-222222222222"
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                Vacancy(
                    vacancy_id=vacancy_id,
                    title="Platform Engineer",
                    description="Build compensation workflows",
                    department="Engineering",
                    status="open",
                    hiring_manager_staff_id=manager_staff_id,
                )
            )
            session.add(
                EmployeeProfile(
                    employee_id=employee_id,
                    hire_conversion_id=str(uuid4()),
                    vacancy_id=vacancy_id,
                    candidate_id=str(uuid4()),
                    first_name="Ada",
                    last_name="Lovelace",
                    email="ada@example.com",
                    phone=None,
                    location="Minsk",
                    current_title="Engineer",
                    extra_data_json={},
                    offer_terms_summary="Offer summary",
                    start_date=date(2026, 4, 1),
                    created_by_staff_id="hr-1",
                )
            )
            session.commit()
    finally:
        engine.dispose()
    return {
        "manager_staff_id": manager_staff_id,
        "employee_id": employee_id,
        "vacancy_id": vacancy_id,
    }


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for compensation integration tests."""
    configured, _, _ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_compensation_raise_and_table_flow(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify raise approval updates compensation table and audit events."""
    _, context_holder, database_url = configured_app
    employee_id = UUID("22222222-2222-4222-8222-222222222222")
    vacancy_id = UUID("11111111-1111-4111-8111-111111111111")

    context_holder["context"] = AuthContext(
        subject_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    create_response = await api_client.post(
        "/api/v1/compensation/raises",
        json={
            "employee_id": str(employee_id),
            "proposed_base_salary": 2200.0,
            "effective_date": date.today().isoformat(),
        },
    )
    assert create_response.status_code == 200
    request_id = create_response.json()["request_id"]

    confirm_response = await api_client.post(
        f"/api/v1/compensation/raises/{request_id}/confirm",
    )
    assert confirm_response.status_code == 200

    context_holder["context"] = AuthContext(
        subject_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    confirm_response = await api_client.post(
        f"/api/v1/compensation/raises/{request_id}/confirm",
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "awaiting_leader"

    context_holder["context"] = AuthContext(
        subject_id=UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        role="leader",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    approve_response = await api_client.post(
        f"/api/v1/compensation/raises/{request_id}/approve",
        json={"note": "Approved"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    context_holder["context"] = AuthContext(
        subject_id=UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
        role="hr",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    band_response = await api_client.post(
        "/api/v1/compensation/salary-bands",
        json={
            "vacancy_id": str(vacancy_id),
            "min_amount": 1800.0,
            "max_amount": 2600.0,
        },
    )
    assert band_response.status_code == 200

    bonus_response = await api_client.post(
        "/api/v1/compensation/bonuses",
        json={
            "employee_id": str(employee_id),
            "period_month": date(2026, 4, 1).isoformat(),
            "amount": 300.0,
            "note": "April bonus",
        },
    )
    assert bonus_response.status_code == 200

    table_response = await api_client.get("/api/v1/compensation/table")
    assert table_response.status_code == 200
    payload = table_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["base_salary"] == 2200.0
    assert payload["items"][0]["bonus_amount"] == 300.0
    assert payload["items"][0]["band_alignment_status"] == "within_band"

    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            events = list(session.execute(select(AuditEvent)).scalars())
    finally:
        engine.dispose()
    assert any(
        event.action == "compensation:read" and event.result == "success"
        for event in events
    )


async def test_compensation_raise_backdated_is_audited(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify backdated raise request is rejected and audited."""
    _, context_holder, database_url = configured_app
    context_holder["context"] = AuthContext(
        subject_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    response = await api_client.post(
        "/api/v1/compensation/raises",
        json={
            "employee_id": "22222222-2222-4222-8222-222222222222",
            "proposed_base_salary": 2000.0,
            "effective_date": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 422
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            events = list(session.execute(select(AuditEvent)).scalars())
    finally:
        engine.dispose()
    assert any(
        event.result == "failure"
        and event.reason == "raise_effective_date_backdated"
        for event in events
    )
