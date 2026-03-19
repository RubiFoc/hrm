"""Integration tests for onboarding task APIs."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.automation.models.metric_event import AutomationMetricEvent
from hrm_backend.core.models.base import Base
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.template import OnboardingTemplate, OnboardingTemplateItem
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for onboarding task integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'onboarding_task_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for onboarding task integration tests."""
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
    _seed_active_template(sqlite_database_url)
    seeded = {
        "legacy_run_id": _seed_legacy_onboarding_run(
            sqlite_database_url,
            onboarding_id="11111111-1111-4111-8111-111111111111",
        ),
        "missing_template_run_id": _seed_legacy_onboarding_run(
            sqlite_database_url,
            onboarding_id="22222222-2222-4222-8222-222222222222",
        ),
    }
    try:
        yield app, context_holder, sqlite_database_url, seeded
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


def _seed_active_template(database_url: str) -> str:
    """Insert one active onboarding checklist template for task API tests."""
    template_id = "33333333-3333-4333-8333-333333333333"
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                OnboardingTemplate(
                    template_id=template_id,
                    name="Default onboarding",
                    description="Core employee ramp-up checklist.",
                    is_active=True,
                    created_by_staff_id="44444444-4444-4444-8444-444444444444",
                )
            )
            session.add_all(
                [
                    OnboardingTemplateItem(
                        template_item_id="55555555-5555-4555-8555-555555555555",
                        template_id=template_id,
                        code="accounts",
                        title="Create accounts",
                        description="Provision required systems",
                        sort_order=20,
                        is_required=True,
                    ),
                    OnboardingTemplateItem(
                        template_item_id="66666666-6666-4666-8666-666666666666",
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


def _seed_legacy_onboarding_run(database_url: str, *, onboarding_id: str) -> str:
    """Insert one legacy onboarding run without task rows."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                OnboardingRun(
                    onboarding_id=onboarding_id,
                    employee_id=str(uuid4()),
                    hire_conversion_id=str(uuid4()),
                    status="started",
                    started_by_staff_id=str(uuid4()),
                )
            )
            session.commit()
    finally:
        engine.dispose()

    return onboarding_id


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


def _load_tasks(database_url: str, *, onboarding_id: str) -> list[OnboardingTask]:
    """Load ordered onboarding task rows for one onboarding run."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            return list(
                session.execute(
                    select(OnboardingTask)
                    .filter(OnboardingTask.onboarding_id == onboarding_id)
                    .order_by(OnboardingTask.sort_order.asc(), OnboardingTask.task_id.asc())
                ).scalars()
            )
    finally:
        engine.dispose()


def _load_metric_events(database_url: str) -> list[AutomationMetricEvent]:
    """Load ordered automation KPI metric rows from database URL."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            return list(
                session.execute(
                    select(AutomationMetricEvent).order_by(
                        AutomationMetricEvent.event_time.asc(),
                        AutomationMetricEvent.metric_event_id.asc(),
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


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for onboarding task integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_onboarding_task_api_backfills_lists_and_updates_tasks(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify staff task API can backfill, read, and patch onboarding tasks."""
    _, _, database_url, seeded = configured_app
    onboarding_id = seeded["legacy_run_id"]

    backfill_response = await api_client.post(
        f"/api/v1/onboarding/runs/{onboarding_id}/tasks/backfill"
    )
    assert backfill_response.status_code == 200
    backfill_payload = backfill_response.json()
    assert [item["code"] for item in backfill_payload["items"]] == ["intro", "accounts"]
    assert all(item["status"] == "pending" for item in backfill_payload["items"])

    list_response = await api_client.get(f"/api/v1/onboarding/runs/{onboarding_id}/tasks")
    assert list_response.status_code == 200
    listed_items = list_response.json()["items"]
    assert [item["code"] for item in listed_items] == ["intro", "accounts"]

    first_task = listed_items[0]
    update_response = await api_client.patch(
        f"/api/v1/onboarding/runs/{onboarding_id}/tasks/{first_task['task_id']}",
        json={
            "status": "completed",
            "assigned_role": "hr",
            "assigned_staff_id": "77777777-7777-4777-8777-777777777777",
            "due_at": "2026-04-02T09:00:00Z",
        },
    )
    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["status"] == "completed"
    assert updated_payload["assigned_role"] == "hr"
    assert updated_payload["assigned_staff_id"] == "77777777-7777-4777-8777-777777777777"
    assert updated_payload["due_at"].startswith("2026-04-02T09:00:00")
    assert updated_payload["completed_at"] is not None

    reopen_response = await api_client.patch(
        f"/api/v1/onboarding/runs/{onboarding_id}/tasks/{first_task['task_id']}",
        json={
            "status": "in_progress",
            "assigned_role": None,
            "assigned_staff_id": None,
            "due_at": None,
        },
    )
    assert reopen_response.status_code == 200
    reopened_payload = reopen_response.json()
    assert reopened_payload["status"] == "in_progress"
    assert reopened_payload["assigned_role"] is None
    assert reopened_payload["assigned_staff_id"] is None
    assert reopened_payload["due_at"] is None
    assert reopened_payload["completed_at"] is None

    persisted_tasks = _load_tasks(database_url, onboarding_id=onboarding_id)
    assert len(persisted_tasks) == 2
    assert persisted_tasks[0].status == "in_progress"

    metric_events = _load_metric_events(database_url)
    assert len(metric_events) == 1
    assert metric_events[0].event_type == "onboarding.task_assigned"
    assert metric_events[0].total_hr_operations_count == 1
    assert metric_events[0].automated_hr_operations_count == 0
    assert metric_events[0].outcome == "no_rules"

    events = _load_events(database_url)
    success_actions = [
        (event.action, event.result)
        for event in events
        if event.resource_type == "onboarding_task"
    ]
    assert ("onboarding_task:backfill", "success") in success_actions
    assert ("onboarding_task:list", "success") in success_actions
    assert ("onboarding_task:update", "success") in success_actions


async def test_onboarding_task_api_reports_conflicts_missing_template_and_rbac_denials(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify onboarding task API keeps stable conflict, error, and RBAC contracts."""
    _, context_holder, database_url, seeded = configured_app
    onboarding_id = seeded["legacy_run_id"]
    missing_template_run_id = seeded["missing_template_run_id"]

    first_backfill = await api_client.post(
        f"/api/v1/onboarding/runs/{onboarding_id}/tasks/backfill"
    )
    assert first_backfill.status_code == 200

    duplicate_backfill = await api_client.post(
        f"/api/v1/onboarding/runs/{onboarding_id}/tasks/backfill"
    )
    assert duplicate_backfill.status_code == 409
    assert duplicate_backfill.json()["detail"] == "onboarding_tasks_already_exist"

    missing_run = await api_client.get(
        "/api/v1/onboarding/runs/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/tasks"
    )
    assert missing_run.status_code == 404
    assert missing_run.json()["detail"] == "onboarding_run_not_found"

    _deactivate_all_templates(database_url)
    missing_template_backfill = await api_client.post(
        f"/api/v1/onboarding/runs/{missing_template_run_id}/tasks/backfill"
    )
    assert missing_template_backfill.status_code == 422
    assert missing_template_backfill.json()["detail"] == "onboarding_template_not_configured"

    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    forbidden_list = await api_client.get(f"/api/v1/onboarding/runs/{onboarding_id}/tasks")
    assert forbidden_list.status_code == 403

    events = _load_events(database_url)
    denied_events = [
        event
        for event in events
        if event.action == "onboarding_task:list" and event.result == "denied"
    ]
    assert len(denied_events) == 1
    assert denied_events[0].actor_role == "manager"
