"""Integration tests for automation rule CRUD and RBAC enforcement."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.automation.dao.automation_rule_dao import AutomationRuleDAO
from hrm_backend.automation.schemas.events import (
    PipelineTransitionAppendedEvent,
    PipelineTransitionAppendedPayload,
)
from hrm_backend.automation.services.evaluator import AutomationEvaluator
from hrm_backend.automation.services.executor import AutomationActionExecutor
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.notifications.dao.notification_dao import NotificationDAO
from hrm_backend.notifications.models.notification import Notification
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
        yield app, context_holder, sqlite_database_url
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


def _seed_manager_and_candidate(database_url: str) -> dict[str, str]:
    """Insert one manager account and one candidate profile for pipeline automation tests."""
    manager_id = "11111111-1111-4111-8111-111111111111"
    candidate_id = "22222222-2222-4222-8222-222222222222"
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            session.add(
                StaffAccount(
                    staff_id=manager_id,
                    login="manager-rule",
                    email="manager-rule@example.com",
                    password_hash="hash",
                    role="manager",
                    is_active=True,
                )
            )
            session.add(
                CandidateProfile(
                    candidate_id=candidate_id,
                    owner_subject_id="candidate-owner",
                    first_name="Rule",
                    last_name="Candidate",
                    email="rule-candidate@example.com",
                    phone=None,
                    location=None,
                    current_title=None,
                    extra_data={},
                )
            )
            session.commit()
    finally:
        engine.dispose()
    return {"manager_id": manager_id, "candidate_id": candidate_id}


def _count_notifications(database_url: str, *, recipient_staff_id: str, kind: str) -> int:
    """Count notifications by recipient and kind from a dedicated DB session."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            return (
                session.query(Notification)
                .filter(
                    Notification.recipient_staff_id == recipient_staff_id,
                    Notification.kind == kind,
                )
                .count()
            )
    finally:
        engine.dispose()


def _retry_pipeline_event(
    database_url: str,
    *,
    transition_id: str,
    transitioned_at: str,
    vacancy_id: str,
    vacancy_title: str,
    candidate_id: str,
    changed_by_staff_id: str,
    changed_by_role: str,
    manager_id: str,
) -> int:
    """Replay one pipeline trigger event through the real executor for retry semantics checks."""
    parsed_event_time = datetime.fromisoformat(transitioned_at.replace("Z", "+00:00"))
    event_time = (
        parsed_event_time.replace(tzinfo=UTC)
        if parsed_event_time.tzinfo is None
        else parsed_event_time.astimezone(UTC)
    )
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            evaluator = AutomationEvaluator(
                rule_dao=AutomationRuleDAO(session=session),
                staff_account_dao=StaffAccountDAO(session=session),
            )
            executor = AutomationActionExecutor(
                evaluator=evaluator,
                notification_dao=NotificationDAO(session=session),
            )
            event = PipelineTransitionAppendedEvent(
                event_type="pipeline.transition_appended",
                event_time=event_time,
                trigger_event_id=UUID(transition_id),
                payload=PipelineTransitionAppendedPayload(
                    transition_id=UUID(transition_id),
                    vacancy_id=UUID(vacancy_id),
                    vacancy_title=vacancy_title,
                    candidate_id=UUID(candidate_id),
                    candidate_id_short=candidate_id.split("-")[0],
                    from_stage=None,
                    to_stage="applied",
                    stage="applied",
                    hiring_manager_staff_id=UUID(manager_id),
                    changed_by_staff_id=changed_by_staff_id,
                    changed_by_role=changed_by_role,
                ),
            )
            return executor.handle_event(event=event, correlation_id="integration-retry")
    finally:
        engine.dispose()


async def test_hr_can_crud_and_activate_rules(configured_app):
    """Verify HR role can create/list/update/activate automation rules."""
    configured, _, _ = configured_app
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
    configured, context_holder, _ = configured_app
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


async def test_pipeline_rule_emits_once_and_retry_of_same_event_is_deduped(configured_app):
    """Verify API-triggered automation emits once and retrying same trigger event is idempotent."""
    configured, context_holder, database_url = configured_app
    seeded = _seed_manager_and_candidate(database_url)

    transport = ASGITransport(app=configured)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_rule_response = await client.post(
            "/api/v1/automation/rules",
            json={
                "name": "Notify manager on applied",
                "trigger": "pipeline.transition_appended",
                "conditions": {"op": "eq", "field": "stage", "value": "applied"},
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
                "priority": 100,
            },
        )
        assert create_rule_response.status_code == 200
        rule_id = create_rule_response.json()["rule_id"]

        activate_response = await client.post(
            f"/api/v1/automation/rules/{rule_id}/activation",
            json={"is_active": True},
        )
        assert activate_response.status_code == 200
        assert activate_response.json()["is_active"] is True

        create_vacancy_response = await client.post(
            "/api/v1/vacancies",
            json={
                "title": "Reliability Engineer",
                "description": "Build resilient automation.",
                "department": "Engineering",
                "status": "open",
            },
        )
        assert create_vacancy_response.status_code == 200
        vacancy_id = create_vacancy_response.json()["vacancy_id"]

        assign_manager_response = await client.patch(
            f"/api/v1/vacancies/{vacancy_id}",
            json={"hiring_manager_login": "manager-rule"},
        )
        assert assign_manager_response.status_code == 200

        transition_response = await client.post(
            "/api/v1/pipeline/transitions",
            json={
                "vacancy_id": vacancy_id,
                "candidate_id": seeded["candidate_id"],
                "to_stage": "applied",
                "reason": "initial_apply",
            },
        )
        assert transition_response.status_code == 200
        transition_payload = transition_response.json()
        assert transition_payload["to_stage"] == "applied"

        context_holder["context"] = AuthContext(
            subject_id=UUID(seeded["manager_id"]),
            role="manager",
            session_id=uuid4(),
            token_id=uuid4(),
            expires_at=9999999999,
        )
        unread_response = await client.get("/api/v1/notifications?status=unread&limit=20&offset=0")
        assert unread_response.status_code == 200
        unread_items = unread_response.json()["items"]
        assert any(item["kind"] == "pipeline_stage_changed" for item in unread_items)

        emitted_before_retry = _count_notifications(
            database_url,
            recipient_staff_id=seeded["manager_id"],
            kind="pipeline_stage_changed",
        )
        assert emitted_before_retry == 1

        retry_created = _retry_pipeline_event(
            database_url,
            transition_id=transition_payload["transition_id"],
            transitioned_at=transition_payload["transitioned_at"],
            vacancy_id=vacancy_id,
            vacancy_title="Reliability Engineer",
            candidate_id=seeded["candidate_id"],
            changed_by_staff_id=transition_payload["changed_by_sub"],
            changed_by_role=transition_payload["changed_by_role"],
            manager_id=seeded["manager_id"],
        )
        assert retry_created == 0

        emitted_after_retry = _count_notifications(
            database_url,
            recipient_staff_id=seeded["manager_id"],
            kind="pipeline_stage_changed",
        )
        assert emitted_after_retry == 1
