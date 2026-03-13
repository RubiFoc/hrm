"""Integration tests for recipient-scoped notification APIs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for notification integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'notifications_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for notification integration tests."""
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
        yield app, context_holder, engine
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for notification integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


def _seed_staff_accounts(engine) -> dict[str, str]:
    """Insert manager/accountant fixture accounts used by API tests."""
    manager_id = "11111111-1111-4111-8111-111111111111"
    manager_beta_id = "12121212-1212-4212-8212-121212121212"
    accountant_id = "22222222-2222-4222-8222-222222222222"
    with Session(engine) as session:
        session.add_all(
            [
                StaffAccount(
                    staff_id=manager_id,
                    login="manager-alpha",
                    email="manager-alpha@example.com",
                    password_hash="hash",
                    role="manager",
                    is_active=True,
                ),
                StaffAccount(
                    staff_id=manager_beta_id,
                    login="manager-beta",
                    email="manager-beta@example.com",
                    password_hash="hash",
                    role="manager",
                    is_active=True,
                ),
                StaffAccount(
                    staff_id=accountant_id,
                    login="accountant-alpha",
                    email="accountant@example.com",
                    password_hash="hash",
                    role="accountant",
                    is_active=True,
                ),
                StaffAccount(
                    staff_id="33333333-3333-4333-8333-333333333333",
                    login="hr-user",
                    email="hr@example.com",
                    password_hash="hash",
                    role="hr",
                    is_active=True,
                ),
            ]
        )
        session.commit()
    return {
        "manager_id": manager_id,
        "manager_beta_id": manager_beta_id,
        "accountant_id": accountant_id,
    }


def _seed_onboarding_task(engine) -> dict[str, str]:
    """Insert one onboarding run and unassigned task for accountant notification tests."""
    onboarding_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    task_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    with Session(engine) as session:
        session.add(
            OnboardingRun(
                onboarding_id=onboarding_id,
                employee_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                hire_conversion_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
                status="started",
                started_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
                started_by_staff_id="33333333-3333-4333-8333-333333333333",
            )
        )
        session.add(
            OnboardingTask(
                task_id=task_id,
                onboarding_id=onboarding_id,
                template_id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
                template_item_id="ffffffff-ffff-4fff-8fff-ffffffffffff",
                code="collect_bank_details",
                title="Collect bank details",
                description=None,
                sort_order=10,
                is_required=True,
                status="pending",
                assigned_role=None,
                assigned_staff_id=None,
                due_at=None,
                completed_at=None,
                created_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
                updated_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
            )
        )
        session.commit()
    return {"onboarding_id": onboarding_id, "task_id": task_id}


async def test_manager_notifications_api_is_fail_closed_and_supports_mark_read(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify manager notification reads stay recipient-scoped and support mark-read flow."""
    _, context_holder, engine = configured_app
    staff_ids = _seed_staff_accounts(engine)

    create_response = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": "Platform Engineer",
            "description": "Build platform foundations.",
            "department": "Engineering",
            "status": "open",
        },
    )
    assert create_response.status_code == 200
    vacancy_id = create_response.json()["vacancy_id"]

    patch_response = await api_client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        json={"hiring_manager_login": "manager-alpha"},
    )
    assert patch_response.status_code == 200

    context_holder["context"] = AuthContext(
        subject_id=staff_ids["manager_id"],
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    unread_response = await api_client.get("/api/v1/notifications?status=unread&limit=20&offset=0")
    assert unread_response.status_code == 200
    unread_payload = unread_response.json()
    assert unread_payload["total"] == 1
    assert unread_payload["unread_count"] == 1
    notification_id = unread_payload["items"][0]["notification_id"]
    assert unread_payload["items"][0]["kind"] == "vacancy_assignment"

    digest_response = await api_client.get("/api/v1/notifications/digest")
    assert digest_response.status_code == 200
    digest_payload = digest_response.json()
    assert digest_payload["summary"]["unread_notification_count"] == 1
    assert digest_payload["summary"]["owned_open_vacancy_count"] == 1

    read_response = await api_client.post(f"/api/v1/notifications/{notification_id}/read")
    assert read_response.status_code == 200
    assert read_response.json()["status"] == "read"

    context_holder["context"] = AuthContext(
        subject_id=staff_ids["manager_beta_id"],
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    denied_read_response = await api_client.post(f"/api/v1/notifications/{notification_id}/read")
    assert denied_read_response.status_code == 404
    assert denied_read_response.json()["detail"] == "notification_not_found"


async def test_accountant_notifications_emit_only_on_assignment_changes(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify accountant notifications are emitted on assignment change and deduped otherwise."""
    _, context_holder, engine = configured_app
    staff_ids = _seed_staff_accounts(engine)
    onboarding_ids = _seed_onboarding_task(engine)

    update_response = await api_client.patch(
        f"/api/v1/onboarding/runs/{onboarding_ids['onboarding_id']}/tasks/{onboarding_ids['task_id']}",
        json={"assigned_role": "accountant"},
    )
    assert update_response.status_code == 200

    due_at = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    due_date_response = await api_client.patch(
        f"/api/v1/onboarding/runs/{onboarding_ids['onboarding_id']}/tasks/{onboarding_ids['task_id']}",
        json={"due_at": due_at},
    )
    assert due_date_response.status_code == 200

    repeat_assignment_response = await api_client.patch(
        f"/api/v1/onboarding/runs/{onboarding_ids['onboarding_id']}/tasks/{onboarding_ids['task_id']}",
        json={"assigned_role": "accountant"},
    )
    assert repeat_assignment_response.status_code == 200

    context_holder["context"] = AuthContext(
        subject_id=staff_ids["accountant_id"],
        role="accountant",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    all_response = await api_client.get("/api/v1/notifications?status=all&limit=20&offset=0")
    assert all_response.status_code == 200
    payload = all_response.json()
    assert payload["total"] == 1
    assert payload["unread_count"] == 1
    assert payload["items"][0]["kind"] == "onboarding_task_assignment"
    assert payload["items"][0]["payload"]["task_title"] == "Collect bank details"

    digest_response = await api_client.get("/api/v1/notifications/digest")
    assert digest_response.status_code == 200
    digest_payload = digest_response.json()
    assert digest_payload["summary"]["unread_notification_count"] == 1
    assert digest_payload["summary"]["active_task_count"] == 1
    assert digest_payload["summary"]["owned_open_vacancy_count"] == 0
