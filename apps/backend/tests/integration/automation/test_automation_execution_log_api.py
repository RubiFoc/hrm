"""Integration tests for automation execution log read APIs and RBAC enforcement."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.automation.models.action_execution import AutomationActionExecution
from hrm_backend.automation.models.execution_run import AutomationExecutionRun
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'automation_execution_logs.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides and seed one execution run/action row."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
    )
    context_holder: dict[str, AuthContext] = {
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

    run_id = uuid4()
    action_execution_id = uuid4()
    trigger_event_id = uuid4()
    now = datetime(2026, 3, 16, 12, 0, tzinfo=UTC)
    with Session(engine) as session:
        run = AutomationExecutionRun(
            run_id=str(run_id),
            event_type="pipeline.transition_appended",
            trigger_event_id=str(trigger_event_id),
            event_time=now,
            correlation_id="req-int-1",
            trace_id="trace-int-1",
            status="succeeded",
            planned_action_count=1,
            succeeded_action_count=1,
            deduped_action_count=0,
            failed_action_count=0,
            started_at=now,
            finished_at=now,
            updated_at=now,
        )
        session.add(run)
        session.add(
            AutomationActionExecution(
                action_execution_id=str(action_execution_id),
                run_id=str(run_id),
                action="notification.emit",
                rule_id=str(uuid4()),
                recipient_staff_id=str(uuid4()),
                recipient_role="manager",
                source_type="pipeline_transition",
                source_id=str(trigger_event_id),
                dedupe_key="rule:seed",
                status="succeeded",
                attempt_count=1,
                trace_id="trace-int-1",
                result_notification_id=str(uuid4()),
                error_kind=None,
                error_text=None,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    try:
        yield app, context_holder, run_id, action_execution_id
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


async def test_hr_can_list_and_read_execution_logs(configured_app):
    """Verify HR role can list and read automation execution logs."""
    configured, _, run_id, action_execution_id = configured_app
    transport = ASGITransport(app=configured)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        list_response = await client.get("/api/v1/automation/executions")
        assert list_response.status_code == 200
        payload = list_response.json()
        assert payload["total"] == 1
        assert payload["items"][0]["run_id"] == str(run_id)

        filter_response = await client.get(
            "/api/v1/automation/executions",
            params={"event_type": "pipeline.transition_appended"},
        )
        assert filter_response.status_code == 200
        assert filter_response.json()["total"] == 1

        run_response = await client.get(f"/api/v1/automation/executions/{run_id}")
        assert run_response.status_code == 200
        assert run_response.json()["run_id"] == str(run_id)

        actions_response = await client.get(f"/api/v1/automation/executions/{run_id}/actions")
        assert actions_response.status_code == 200
        assert actions_response.json()["total"] == 1

        action_response = await client.get(
            f"/api/v1/automation/action-executions/{action_execution_id}"
        )
        assert action_response.status_code == 200
        assert action_response.json()["action_execution_id"] == str(action_execution_id)


async def test_manager_is_denied_for_execution_log_list(configured_app):
    """Verify non-privileged roles are denied for execution log read APIs."""
    configured, context_holder, run_id, _ = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    transport = ASGITransport(app=configured)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/automation/executions")
        assert response.status_code == 403

        response = await client.get(f"/api/v1/automation/executions/{run_id}")
        assert response.status_code == 403

