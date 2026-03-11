"""Integration tests for onboarding checklist template APIs."""

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
from hrm_backend.core.models.base import Base
from hrm_backend.employee.models.template import OnboardingTemplate, OnboardingTemplateItem
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for onboarding template integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'onboarding_template_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for onboarding template integration tests."""
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
    try:
        yield app, context_holder, sqlite_database_url
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
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


def _load_templates(database_url: str) -> list[OnboardingTemplate]:
    """Load ordered onboarding template rows from database URL."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            return list(
                session.execute(
                    select(OnboardingTemplate).order_by(
                        OnboardingTemplate.created_at.asc(),
                        OnboardingTemplate.template_id.asc(),
                    )
                ).scalars()
            )
    finally:
        engine.dispose()


def _load_template_items(database_url: str) -> list[OnboardingTemplateItem]:
    """Load ordered onboarding template item rows from database URL."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            return list(
                session.execute(
                    select(OnboardingTemplateItem).order_by(
                        OnboardingTemplateItem.template_id.asc(),
                        OnboardingTemplateItem.sort_order.asc(),
                        OnboardingTemplateItem.template_item_id.asc(),
                    )
                ).scalars()
            )
    finally:
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for onboarding template integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_onboarding_template_api_creates_reads_lists_and_switches_active_template(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify onboarding templates can be created, read, listed, and re-activated."""
    _, _, database_url = configured_app

    first_create = await api_client.post(
        "/api/v1/onboarding/templates",
        json={
            "name": "Default onboarding",
            "description": "Core employee ramp-up checklist.",
            "is_active": True,
            "items": [
                {
                    "code": "accounts",
                    "title": "Create accounts",
                    "description": "Provision required systems",
                    "sort_order": 20,
                    "is_required": True,
                },
                {
                    "code": "intro",
                    "title": "Team intro",
                    "description": None,
                    "sort_order": 10,
                    "is_required": False,
                },
            ],
        },
    )
    assert first_create.status_code == 200
    first_payload = first_create.json()
    assert first_payload["is_active"] is True
    assert [item["code"] for item in first_payload["items"]] == ["intro", "accounts"]

    second_create = await api_client.post(
        "/api/v1/onboarding/templates",
        json={
            "name": "Remote onboarding",
            "description": "Checklist for remote hires.",
            "is_active": False,
            "items": [
                {
                    "code": "equipment",
                    "title": "Ship equipment",
                    "description": "Send laptop and accessories",
                    "sort_order": 10,
                    "is_required": True,
                }
            ],
        },
    )
    assert second_create.status_code == 200
    second_payload = second_create.json()
    assert second_payload["is_active"] is False

    update_second = await api_client.put(
        f"/api/v1/onboarding/templates/{second_payload['template_id']}",
        json={
            "name": "Remote onboarding v2",
            "description": "Updated checklist for remote hires.",
            "is_active": True,
            "items": [
                {
                    "code": "equipment",
                    "title": "Ship equipment",
                    "description": "Send laptop and accessories",
                    "sort_order": 10,
                    "is_required": True,
                },
                {
                    "code": "security",
                    "title": "Security briefing",
                    "description": "Review MFA and device policies",
                    "sort_order": 20,
                    "is_required": True,
                },
            ],
        },
    )
    assert update_second.status_code == 200
    updated_second_payload = update_second.json()
    assert updated_second_payload["name"] == "Remote onboarding v2"
    assert updated_second_payload["is_active"] is True
    assert [item["code"] for item in updated_second_payload["items"]] == [
        "equipment",
        "security",
    ]

    first_read = await api_client.get(
        f"/api/v1/onboarding/templates/{first_payload['template_id']}"
    )
    assert first_read.status_code == 200
    assert first_read.json()["is_active"] is False

    active_list = await api_client.get("/api/v1/onboarding/templates?active_only=true")
    assert active_list.status_code == 200
    active_items = active_list.json()["items"]
    assert len(active_items) == 1
    assert active_items[0]["template_id"] == second_payload["template_id"]
    assert active_items[0]["name"] == "Remote onboarding v2"

    templates = _load_templates(database_url)
    assert len(templates) == 2
    active_templates = [template for template in templates if template.is_active]
    assert len(active_templates) == 1
    assert active_templates[0].template_id == second_payload["template_id"]

    items = _load_template_items(database_url)
    second_items = [item for item in items if item.template_id == second_payload["template_id"]]
    assert [item.code for item in second_items] == ["equipment", "security"]

    events = _load_events(database_url)
    success_actions = [
        (event.action, event.result)
        for event in events
        if event.resource_type == "onboarding_template"
    ]
    assert ("onboarding_template:create", "success") in success_actions
    assert ("onboarding_template:update", "success") in success_actions
    assert ("onboarding_template:read", "success") in success_actions
    assert ("onboarding_template:list", "success") in success_actions


async def test_onboarding_template_api_reports_conflicts_validation_and_rbac_denials(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify onboarding template API keeps stable conflict, validation, and RBAC errors."""
    _, context_holder, database_url = configured_app

    first_create = await api_client.post(
        "/api/v1/onboarding/templates",
        json={
            "name": "Default onboarding",
            "description": "Core employee ramp-up checklist.",
            "is_active": True,
            "items": [
                {
                    "code": "intro",
                    "title": "Team intro",
                    "description": None,
                    "sort_order": 10,
                    "is_required": True,
                }
            ],
        },
    )
    assert first_create.status_code == 200

    duplicate_name = await api_client.post(
        "/api/v1/onboarding/templates",
        json={
            "name": "Default onboarding",
            "description": "Another template with the same name.",
            "is_active": False,
            "items": [
                {
                    "code": "equipment",
                    "title": "Ship equipment",
                    "description": None,
                    "sort_order": 10,
                    "is_required": True,
                }
            ],
        },
    )
    assert duplicate_name.status_code == 409
    assert duplicate_name.json()["detail"] == "onboarding_template_name_conflict"

    invalid_template = await api_client.post(
        "/api/v1/onboarding/templates",
        json={
            "name": "Broken onboarding",
            "description": "Duplicate item codes must fail.",
            "is_active": False,
            "items": [
                {
                    "code": "intro",
                    "title": "Team intro",
                    "description": None,
                    "sort_order": 10,
                    "is_required": True,
                },
                {
                    "code": "intro",
                    "title": "Second intro",
                    "description": None,
                    "sort_order": 20,
                    "is_required": True,
                },
            ],
        },
    )
    assert invalid_template.status_code == 422
    assert invalid_template.json()["detail"] == "onboarding_template_invalid"

    missing_read = await api_client.get(
        "/api/v1/onboarding/templates/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    )
    assert missing_read.status_code == 404
    assert missing_read.json()["detail"] == "onboarding_template_not_found"

    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    forbidden_list = await api_client.get("/api/v1/onboarding/templates")
    assert forbidden_list.status_code == 403

    events = _load_events(database_url)
    denied_events = [
        event
        for event in events
        if event.action == "onboarding_template:list" and event.result == "denied"
    ]
    assert len(denied_events) == 1
    assert denied_events[0].actor_role == "manager"
