"""Integration tests for ADMIN-02 admin staff list/update APIs and audit hooks."""

from __future__ import annotations

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
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for admin staff integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'admin_staff_management.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure application dependency overrides for SQLite-backed admin tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
    )
    context_holder = {
        "context": AuthContext(
            subject_id=uuid4(),
            role="admin",
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


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide in-process async API client for admin integration tests."""
    configured, _, _ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


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


async def _create_staff(
    client: AsyncClient,
    *,
    login: str,
    role: str,
    is_active: bool = True,
) -> dict[str, object]:
    """Create staff row via admin API and return response payload."""
    response = await client.post(
        "/api/v1/admin/staff",
        json={
            "login": login,
            "email": f"{login}@example.com",
            "password": "StrongPassword!123",
            "role": role,
            "is_active": is_active,
        },
    )
    assert response.status_code == 200
    return response.json()


async def test_admin_can_list_staff_with_filters_and_pagination(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify admin list endpoint applies search/filter/pagination contract."""
    _, context_holder, _ = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    await _create_staff(api_client, login="staff-alpha", role="hr", is_active=True)
    await _create_staff(api_client, login="staff-bravo", role="hr", is_active=False)
    await _create_staff(api_client, login="staff-charlie", role="manager", is_active=True)

    first_page = await api_client.get(
        "/api/v1/admin/staff",
        params={"limit": 1, "offset": 0, "role": "hr"},
    )
    assert first_page.status_code == 200
    first_page_payload = first_page.json()
    assert first_page_payload["limit"] == 1
    assert first_page_payload["offset"] == 0
    assert first_page_payload["total"] == 2
    assert len(first_page_payload["items"]) == 1

    filtered = await api_client.get(
        "/api/v1/admin/staff",
        params={
            "limit": 20,
            "offset": 0,
            "search": "staff-bravo@example.com",
            "role": "hr",
            "is_active": "false",
        },
    )
    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["login"] == "staff-bravo"


async def test_admin_can_patch_staff_role_and_active_state(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify admin can patch role/is_active for another staff account."""
    _, context_holder, _ = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    target = await _create_staff(api_client, login="patch-target", role="hr", is_active=True)

    response = await api_client.patch(
        f"/api/v1/admin/staff/{target['staff_id']}",
        json={"role": "manager", "is_active": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["staff_id"] == target["staff_id"]
    assert payload["role"] == "manager"
    assert payload["is_active"] is False


async def test_strict_guards_return_409_for_self_and_last_admin_cases(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify strict guard rejects self-modification and last-admin deactivation."""
    _, context_holder, _ = configured_app
    self_admin = await _create_staff(api_client, login="self-admin", role="admin", is_active=True)
    self_admin_id = UUID(str(self_admin["staff_id"]))

    context_holder["context"] = AuthContext(
        subject_id=self_admin_id,
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    self_demotion = await api_client.patch(
        f"/api/v1/admin/staff/{self_admin['staff_id']}",
        json={"role": "hr"},
    )
    assert self_demotion.status_code == 409
    assert self_demotion.json()["detail"] == "self_modification_forbidden"

    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    last_admin_disable = await api_client.patch(
        f"/api/v1/admin/staff/{self_admin['staff_id']}",
        json={"is_active": False},
    )
    assert last_admin_disable.status_code == 409
    assert last_admin_disable.json()["detail"] == "last_admin_protection"


async def test_non_admin_gets_403_for_staff_list_and_update(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify non-admin role cannot access admin staff list/update endpoints."""
    _, context_holder, _ = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    target = await _create_staff(api_client, login="forbidden-target", role="hr", is_active=True)

    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="hr",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    list_response = await api_client.get("/api/v1/admin/staff")
    patch_response = await api_client.patch(
        f"/api/v1/admin/staff/{target['staff_id']}",
        json={"role": "manager"},
    )

    assert list_response.status_code == 403
    assert patch_response.status_code == 403


async def test_invalid_staff_id_path_returns_422(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify invalid UUID path parameter returns framework validation error."""
    _, context_holder, _ = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    response = await api_client.patch(
        "/api/v1/admin/staff/not-a-uuid",
        json={"is_active": True},
    )

    assert response.status_code == 422


async def test_admin_staff_audit_events_capture_success_and_failure_reason_codes(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify admin staff list/update audit actions record success/failure reason codes."""
    _, context_holder, database_url = configured_app
    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    target = await _create_staff(api_client, login="audit-target", role="admin", is_active=True)

    list_response = await api_client.get("/api/v1/admin/staff")
    assert list_response.status_code == 200

    success_update = await api_client.patch(
        f"/api/v1/admin/staff/{target['staff_id']}",
        json={"role": "admin", "is_active": True},
    )
    assert success_update.status_code == 200

    context_holder["context"] = AuthContext(
        subject_id=UUID(str(target["staff_id"])),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    failure_update = await api_client.patch(
        f"/api/v1/admin/staff/{target['staff_id']}",
        json={"is_active": False},
    )
    assert failure_update.status_code == 409
    assert failure_update.json()["detail"] == "self_modification_forbidden"

    events = _load_events(database_url)
    list_events = [event for event in events if event.action == "admin.staff:list"]
    update_events = [event for event in events if event.action == "admin.staff:update"]

    assert any(event.result == "success" for event in list_events)
    assert any(event.result == "success" for event in update_events)
    assert any(
        event.result == "failure" and event.reason == "self_modification_forbidden"
        for event in update_events
    )
