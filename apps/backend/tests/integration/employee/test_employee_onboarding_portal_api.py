"""Integration tests for employee self-service onboarding portal APIs."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for employee portal integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'employee_onboarding_portal_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for employee portal integration tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
    )
    employee_staff_id = "11111111-1111-4111-8111-111111111111"
    context_holder = {
        "context": AuthContext(
            subject_id=UUID(employee_staff_id),
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
    seeded = _seed_employee_portal_bundle(sqlite_database_url, employee_staff_id=employee_staff_id)
    try:
        yield app, context_holder, sqlite_database_url, seeded
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


def _seed_employee_portal_bundle(database_url: str, *, employee_staff_id: str) -> dict[str, str]:
    """Insert one employee-role account plus onboarding portal data."""
    employee_id = "22222222-2222-4222-8222-222222222222"
    onboarding_id = "33333333-3333-4333-8333-333333333333"
    actionable_task_id = "44444444-4444-4444-8444-444444444444"
    blocked_task_id = "55555555-5555-4555-8555-555555555555"
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                StaffAccount(
                    staff_id=employee_staff_id,
                    login="ada",
                    email="ada@example.com",
                    password_hash="argon2id$stub",
                    role="employee",
                    is_active=True,
                )
            )
            session.add(
                EmployeeProfile(
                    employee_id=employee_id,
                    hire_conversion_id="66666666-6666-4666-8666-666666666666",
                    vacancy_id="77777777-7777-4777-8777-777777777777",
                    candidate_id="88888888-8888-4888-8888-888888888888",
                    first_name="Ada",
                    last_name="Lovelace",
                    email="ada@example.com",
                    phone="+375291234567",
                    location="Minsk",
                    current_title="Engineer",
                    extra_data_json={"languages": ["ru", "en"]},
                    offer_terms_summary="Base salary 5000 BYN gross.",
                    start_date=None,
                    staff_account_id=None,
                    created_by_staff_id="99999999-9999-4999-8999-999999999999",
                )
            )
            session.add(
                OnboardingRun(
                    onboarding_id=onboarding_id,
                    employee_id=employee_id,
                    hire_conversion_id="66666666-6666-4666-8666-666666666666",
                    status="started",
                    started_by_staff_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                )
            )
            session.add_all(
                [
                    OnboardingTask(
                        task_id=actionable_task_id,
                        onboarding_id=onboarding_id,
                        template_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                        template_item_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                        code="accounts",
                        title="Create accounts",
                        description="Provision employee systems",
                        sort_order=10,
                        is_required=True,
                        status="pending",
                        assigned_role="employee",
                        assigned_staff_id=None,
                    ),
                    OnboardingTask(
                        task_id=blocked_task_id,
                        onboarding_id=onboarding_id,
                        template_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                        template_item_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
                        code="laptop",
                        title="Issue laptop",
                        description="Handled by HR",
                        sort_order=20,
                        is_required=True,
                        status="pending",
                        assigned_role="hr",
                        assigned_staff_id=None,
                    ),
                ]
            )
            session.commit()
    finally:
        engine.dispose()

    return {
        "employee_staff_id": employee_staff_id,
        "employee_id": employee_id,
        "onboarding_id": onboarding_id,
        "actionable_task_id": actionable_task_id,
        "blocked_task_id": blocked_task_id,
    }


def _load_employee_profile(database_url: str, *, employee_id: str) -> EmployeeProfile:
    """Load one employee profile from database URL."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            profile = session.get(EmployeeProfile, employee_id)
            assert profile is not None
            return profile
    finally:
        engine.dispose()


def _load_task(database_url: str, *, task_id: str) -> OnboardingTask:
    """Load one onboarding task from database URL."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            task = session.get(OnboardingTask, task_id)
            assert task is not None
            return task
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


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for employee portal integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_employee_portal_api_reads_tasks_links_identity_and_updates_actionable_task(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify employee portal reads self data, links identity, and updates actionable task."""
    _, _, database_url, seeded = configured_app

    read_response = await api_client.get("/api/v1/employees/me/onboarding")
    assert read_response.status_code == 200
    portal_payload = read_response.json()
    assert portal_payload["employee_id"] == seeded["employee_id"]
    assert portal_payload["onboarding_id"] == seeded["onboarding_id"]
    assert [item["code"] for item in portal_payload["tasks"]] == ["accounts", "laptop"]
    assert [item["can_update"] for item in portal_payload["tasks"]] == [True, False]

    linked_profile = _load_employee_profile(database_url, employee_id=seeded["employee_id"])
    assert linked_profile.staff_account_id == seeded["employee_staff_id"]

    update_response = await api_client.patch(
        f"/api/v1/employees/me/onboarding/tasks/{seeded['actionable_task_id']}",
        json={"status": "completed"},
    )
    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["status"] == "completed"
    assert updated_payload["completed_at"] is not None
    assert updated_payload["can_update"] is True

    updated_task = _load_task(database_url, task_id=seeded["actionable_task_id"])
    assert updated_task.status == "completed"
    assert updated_task.completed_at is not None

    events = _load_events(database_url)
    success_actions = [
        (event.action, event.result)
        for event in events
        if event.action in {"employee_portal:read", "employee_portal:update"}
    ]
    assert ("employee_portal:read", "success") in success_actions
    assert ("employee_portal:update", "success") in success_actions


async def test_employee_portal_api_reports_conflict_missing_and_rbac_denials(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify employee portal preserves missing-profile, actionability, and RBAC deny contracts."""
    _, context_holder, database_url, seeded = configured_app

    blocked_response = await api_client.patch(
        f"/api/v1/employees/me/onboarding/tasks/{seeded['blocked_task_id']}",
        json={"status": "completed"},
    )
    assert blocked_response.status_code == 409
    assert blocked_response.json()["detail"] == "onboarding_task_not_actionable_by_employee"

    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="employee",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    missing_response = await api_client.get("/api/v1/employees/me/onboarding")
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "employee_profile_not_found"

    context_holder["context"] = AuthContext(
        subject_id=UUID(seeded["employee_staff_id"]),
        role="hr",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    denied_response = await api_client.get("/api/v1/employees/me/onboarding")
    assert denied_response.status_code == 403
    assert "employee_portal:read" in denied_response.json()["detail"]

    events = _load_events(database_url)
    failure_actions = [
        (event.action, event.result, event.reason)
        for event in events
        if event.action in {"employee_portal:update", "employee_portal:read"}
    ]
    assert (
        "employee_portal:update",
        "failure",
        "onboarding_task_not_actionable_by_employee",
    ) in failure_actions
    assert ("employee_portal:read", "failure", "employee_profile_not_found") in failure_actions
