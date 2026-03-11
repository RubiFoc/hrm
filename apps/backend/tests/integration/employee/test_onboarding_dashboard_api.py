"""Integration tests for onboarding dashboard APIs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for onboarding dashboard integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'onboarding_dashboard_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for onboarding dashboard integration tests."""
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
    seeded = _seed_dashboard_records(sqlite_database_url)
    try:
        yield app, context_holder, sqlite_database_url, seeded
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


def _seed_dashboard_records(database_url: str) -> dict[str, str]:
    """Insert employee profiles, onboarding runs, and tasks for dashboard API tests."""
    manager_subject_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add_all(
                [
                    EmployeeProfile(
                        employee_id="11111111-1111-4111-8111-111111111111",
                        hire_conversion_id="22222222-2222-4222-8222-222222222222",
                        vacancy_id="33333333-3333-4333-8333-333333333333",
                        candidate_id="44444444-4444-4444-8444-444444444444",
                        first_name="Ada",
                        last_name="Lovelace",
                        email="ada@example.com",
                        phone=None,
                        location="Minsk",
                        current_title="Engineer",
                        extra_data_json={},
                        offer_terms_summary="Laptop and access baseline.",
                        start_date=datetime(2026, 4, 1, tzinfo=UTC).date(),
                        created_by_staff_id="55555555-5555-4555-8555-555555555555",
                    ),
                    EmployeeProfile(
                        employee_id="66666666-6666-4666-8666-666666666666",
                        hire_conversion_id="77777777-7777-4777-8777-777777777777",
                        vacancy_id="88888888-8888-4888-8888-888888888888",
                        candidate_id="99999999-9999-4999-8999-999999999999",
                        first_name="Grace",
                        last_name="Hopper",
                        email="grace@example.com",
                        phone=None,
                        location="Brest",
                        current_title="Engineering Manager",
                        extra_data_json={},
                        offer_terms_summary="Manager onboarding plan.",
                        start_date=datetime(2026, 4, 15, tzinfo=UTC).date(),
                        created_by_staff_id="10101010-1010-4010-8010-101010101010",
                    ),
                ]
            )
            session.add_all(
                [
                    OnboardingRun(
                        onboarding_id="12121212-1212-4212-8212-121212121212",
                        employee_id="11111111-1111-4111-8111-111111111111",
                        hire_conversion_id="22222222-2222-4222-8222-222222222222",
                        status="started",
                        started_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
                        started_by_staff_id="13131313-1313-4313-8313-131313131313",
                    ),
                    OnboardingRun(
                        onboarding_id="14141414-1414-4414-8414-141414141414",
                        employee_id="66666666-6666-4666-8666-666666666666",
                        hire_conversion_id="77777777-7777-4777-8777-777777777777",
                        status="started",
                        started_at=datetime(2026, 3, 11, 9, 0, tzinfo=UTC),
                        started_by_staff_id="15151515-1515-4515-8515-151515151515",
                    ),
                ]
            )
            session.add_all(
                [
                    OnboardingTask(
                        task_id="16161616-1616-4616-8616-161616161616",
                        onboarding_id="12121212-1212-4212-8212-121212121212",
                        template_id="17171717-1717-4717-8717-171717171717",
                        template_item_id="18181818-1818-4818-8818-181818181818",
                        code="manager_intro",
                        title="Manager intro",
                        description="Meet your manager",
                        sort_order=10,
                        is_required=True,
                        status="in_progress",
                        assigned_role="manager",
                        assigned_staff_id=None,
                        due_at=datetime.now(UTC) - timedelta(days=1),
                        completed_at=None,
                    ),
                    OnboardingTask(
                        task_id="19191919-1919-4919-8919-191919191919",
                        onboarding_id="12121212-1212-4212-8212-121212121212",
                        template_id="17171717-1717-4717-8717-171717171717",
                        template_item_id="20202020-2020-4020-8020-202020202020",
                        code="employee_docs",
                        title="Upload documents",
                        description=None,
                        sort_order=20,
                        is_required=True,
                        status="completed",
                        assigned_role="employee",
                        assigned_staff_id=None,
                        due_at=None,
                        completed_at=datetime.now(UTC) - timedelta(hours=4),
                    ),
                    OnboardingTask(
                        task_id="21212121-2121-4212-8212-212121212121",
                        onboarding_id="14141414-1414-4414-8414-141414141414",
                        template_id="22222222-2222-4222-8222-222222222222",
                        template_item_id="23232323-2323-4232-8232-232323232323",
                        code="hr_briefing",
                        title="HR briefing",
                        description="Review policy baseline",
                        sort_order=10,
                        is_required=True,
                        status="pending",
                        assigned_role="hr",
                        assigned_staff_id=manager_subject_id,
                        due_at=datetime.now(UTC) + timedelta(days=2),
                        completed_at=None,
                    ),
                ]
            )
            session.commit()
    finally:
        engine.dispose()

    return {
        "manager_subject_id": manager_subject_id,
        "run_visible_by_role": "12121212-1212-4212-8212-121212121212",
        "run_visible_by_staff": "14141414-1414-4414-8414-141414141414",
    }


def _load_events(database_url: str) -> list[AuditEvent]:
    """Load ordered audit events for assertions."""
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
    """Provide async API client for onboarding dashboard integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_onboarding_dashboard_api_lists_filtered_runs_and_detail(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify HR dashboard API returns filtered list payload and detailed run view."""
    _, _, database_url, seeded = configured_app

    response = await api_client.get(
        "/api/v1/onboarding/runs",
        params={
            "search": "ada",
            "task_status": "in_progress",
            "assigned_role": "manager",
            "overdue_only": "true",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["summary"]["run_count"] == 1
    assert payload["summary"]["overdue_tasks"] == 1
    assert payload["items"][0]["first_name"] == "Ada"
    assert payload["items"][0]["progress_percent"] == 50

    detail_response = await api_client.get(
        f"/api/v1/onboarding/runs/{seeded['run_visible_by_role']}"
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["first_name"] == "Ada"
    assert [task["code"] for task in detail_payload["tasks"]] == [
        "manager_intro",
        "employee_docs",
    ]

    events = _load_events(database_url)
    success_actions = [event.action for event in events if event.result == "success"]
    assert "onboarding_dashboard:list" in success_actions
    assert "onboarding_dashboard:read" in success_actions


async def test_manager_dashboard_visibility_is_scoped_by_assignment(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify manager sees only assigned onboarding runs and gets 404 outside visibility scope."""
    _, context_holder, database_url, seeded = configured_app
    context_holder["context"] = AuthContext(
        subject_id=UUID(seeded["manager_subject_id"]),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    list_response = await api_client.get("/api/v1/onboarding/runs")
    assert list_response.status_code == 200
    listed_ids = [item["onboarding_id"] for item in list_response.json()["items"]]
    assert listed_ids == [
        seeded["run_visible_by_role"],
        seeded["run_visible_by_staff"],
    ]

    hidden_response = await api_client.get(
        "/api/v1/onboarding/runs/ffffffff-ffff-4fff-8fff-ffffffffffff"
    )
    assert hidden_response.status_code == 404
    assert hidden_response.json()["detail"] == "onboarding_run_not_found"

    context_holder["context"] = AuthContext(
        subject_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    invisible_detail = await api_client.get(
        f"/api/v1/onboarding/runs/{seeded['run_visible_by_staff']}"
    )
    assert invisible_detail.status_code == 404
    assert invisible_detail.json()["detail"] == "onboarding_run_not_found"

    events = _load_events(database_url)
    failure_actions = [
        (event.action, event.reason)
        for event in events
        if event.result == "failure"
    ]
    assert ("onboarding_dashboard:read", "onboarding_run_not_found") in failure_actions


async def test_onboarding_dashboard_api_denies_employee_role(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify employee role cannot access staff onboarding dashboard APIs."""
    _, context_holder, database_url, _ = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="employee",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    response = await api_client.get("/api/v1/onboarding/runs")
    assert response.status_code == 403
    assert "Role 'employee' has no permission 'onboarding_dashboard:read'" in response.json()[
        "detail"
    ]

    events = _load_events(database_url)
    denied_actions = [event.action for event in events if event.result == "denied"]
    assert "onboarding_dashboard:read" in denied_actions
