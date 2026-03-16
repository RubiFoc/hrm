"""Integration tests for automation rule CRUD and RBAC enforcement."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'automation_rules.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for automation rule tests."""
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
    with Session(engine) as session:
        session.commit()

    try:
        yield app, context_holder
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


async def test_hr_can_crud_and_activate_rules(configured_app):
    """Verify HR role can create/list/update/activate automation rules."""
    configured, _ = configured_app
    transport = ASGITransport(app=configured)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_payload = {
            "name": "Notify manager on screening",
            "trigger": "pipeline.transition_appended",
            "conditions": {"op": "eq", "field": "stage", "value": "screening"},
            "actions": [
                {
                    "action": "notification.emit",
                    "notification_kind": "pipeline_stage_changed",
                    "title_template": "Pipeline moved to {{stage}}",
                    "body_template": "{{vacancy_title}} candidate {{candidate_id_short}}",
                    "payload_template": {
                        "vacancy_title": "{{vacancy_title}}",
                        "stage": "{{stage}}",
                        "candidate_id_short": "{{candidate_id_short}}",
                    },
                }
            ],
            "priority": 10,
        }
        create_response = await client.post("/api/v1/automation/rules", json=create_payload)
        assert create_response.status_code == 200
        body = create_response.json()
        rule_id = body["rule_id"]
        assert body["is_active"] is False

        list_response = await client.get("/api/v1/automation/rules")
        assert list_response.status_code == 200
        listed = list_response.json()["items"]
        assert any(item["rule_id"] == rule_id for item in listed)

        patch_response = await client.patch(
            f"/api/v1/automation/rules/{rule_id}",
            json={"priority": 5},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["priority"] == 5

        activate_response = await client.post(
            f"/api/v1/automation/rules/{rule_id}/activation",
            json={"is_active": True},
        )
        assert activate_response.status_code == 200
        assert activate_response.json()["is_active"] is True


async def test_manager_is_denied_for_rule_list(configured_app):
    """Verify manager role is denied for automation control plane endpoints."""
    configured, context_holder = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    transport = ASGITransport(app=configured)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/automation/rules")
        assert response.status_code == 403
