"""Integration tests for ADMIN-03 employee-key lifecycle APIs and audit hooks."""

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
from hrm_backend.auth.models.employee_registration_key import EmployeeRegistrationKey
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for admin employee-key integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'admin_employee_key_management.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for SQLite-backed employee-key tests."""
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
    """Provide in-process async API client for employee-key integration tests."""
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


def _set_key_used(database_url: str, key_id: str) -> None:
    """Mark employee registration key as used for revoke-guard validation."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            entity = session.get(EmployeeRegistrationKey, key_id)
            assert entity is not None
            entity.used_at = datetime.now(UTC)
            session.add(entity)
            session.commit()
    finally:
        engine.dispose()


def _set_key_expired(database_url: str, key_id: str) -> None:
    """Move employee registration key expiration into the past."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            entity = session.get(EmployeeRegistrationKey, key_id)
            assert entity is not None
            entity.expires_at = datetime.now(UTC) - timedelta(minutes=1)
            session.add(entity)
            session.commit()
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


async def _create_employee_key(
    client: AsyncClient,
    *,
    target_role: str,
    ttl_seconds: int = 3600,
) -> dict[str, object]:
    """Create employee registration key via admin API and return payload."""
    response = await client.post(
        "/api/v1/admin/employee-keys",
        json={"target_role": target_role, "ttl_seconds": ttl_seconds},
    )
    assert response.status_code == 200
    return response.json()


async def test_admin_and_hr_can_list_and_revoke_employee_keys(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify admin and HR roles can list and revoke employee registration keys."""
    _, context_holder, _ = configured_app

    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    admin_staff = await _create_staff(api_client, login="admin-key-issuer", role="admin")
    hr_staff = await _create_staff(api_client, login="hr-key-issuer", role="hr")

    context_holder["context"] = AuthContext(
        subject_id=UUID(str(admin_staff["staff_id"])),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    admin_key = await _create_employee_key(api_client, target_role="employee")

    admin_list = await api_client.get(
        "/api/v1/admin/employee-keys",
        params={"limit": 20, "offset": 0, "status": "active"},
    )
    assert admin_list.status_code == 200
    admin_payload = admin_list.json()
    assert admin_payload["total"] >= 1
    assert any(item["key_id"] == admin_key["key_id"] for item in admin_payload["items"])

    admin_revoke = await api_client.post(
        f"/api/v1/admin/employee-keys/{admin_key['key_id']}/revoke"
    )
    assert admin_revoke.status_code == 200
    assert admin_revoke.json()["status"] == "revoked"

    context_holder["context"] = AuthContext(
        subject_id=UUID(str(hr_staff["staff_id"])),
        role="hr",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    hr_key = await _create_employee_key(api_client, target_role="manager")

    hr_list = await api_client.get(
        "/api/v1/admin/employee-keys",
        params={"limit": 20, "offset": 0, "created_by_staff_id": hr_staff["staff_id"]},
    )
    assert hr_list.status_code == 200
    hr_payload = hr_list.json()
    assert any(item["key_id"] == hr_key["key_id"] for item in hr_payload["items"])

    hr_revoke = await api_client.post(f"/api/v1/admin/employee-keys/{hr_key['key_id']}/revoke")
    assert hr_revoke.status_code == 200
    assert hr_revoke.json()["status"] == "revoked"


async def test_non_privileged_roles_get_403_for_employee_key_list_and_revoke(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify manager role is denied for employee-key list and revoke endpoints."""
    _, context_holder, _ = configured_app

    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    admin_staff = await _create_staff(api_client, login="admin-deny-source", role="admin")
    manager_staff = await _create_staff(api_client, login="manager-deny-user", role="manager")

    context_holder["context"] = AuthContext(
        subject_id=UUID(str(admin_staff["staff_id"])),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    key = await _create_employee_key(api_client, target_role="employee")

    context_holder["context"] = AuthContext(
        subject_id=UUID(str(manager_staff["staff_id"])),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    list_response = await api_client.get("/api/v1/admin/employee-keys")
    revoke_response = await api_client.post(f"/api/v1/admin/employee-keys/{key['key_id']}/revoke")

    assert list_response.status_code == 403
    assert revoke_response.status_code == 403


async def test_employee_key_revoke_records_audit_reason_codes(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify revoke endpoint writes success/failure audit events with reason codes."""
    _, context_holder, database_url = configured_app

    context_holder["context"] = AuthContext(
        subject_id=uuid4(),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    admin_staff = await _create_staff(api_client, login="admin-audit-issuer", role="admin")
    context_holder["context"] = AuthContext(
        subject_id=UUID(str(admin_staff["staff_id"])),
        role="admin",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )

    active_key = await _create_employee_key(api_client, target_role="employee")
    used_key = await _create_employee_key(api_client, target_role="employee")
    expired_key = await _create_employee_key(api_client, target_role="employee")

    _set_key_used(database_url, str(used_key["key_id"]))
    _set_key_expired(database_url, str(expired_key["key_id"]))

    list_response = await api_client.get("/api/v1/admin/employee-keys")
    assert list_response.status_code == 200

    first_revoke = await api_client.post(
        f"/api/v1/admin/employee-keys/{active_key['key_id']}/revoke"
    )
    assert first_revoke.status_code == 200

    already_revoked = await api_client.post(
        f"/api/v1/admin/employee-keys/{active_key['key_id']}/revoke"
    )
    assert already_revoked.status_code == 409
    assert already_revoked.json()["detail"] == "key_already_revoked"

    already_used = await api_client.post(
        f"/api/v1/admin/employee-keys/{used_key['key_id']}/revoke"
    )
    assert already_used.status_code == 409
    assert already_used.json()["detail"] == "key_already_used"

    already_expired = await api_client.post(
        f"/api/v1/admin/employee-keys/{expired_key['key_id']}/revoke"
    )
    assert already_expired.status_code == 409
    assert already_expired.json()["detail"] == "key_already_expired"

    unknown_key = await api_client.post(f"/api/v1/admin/employee-keys/{uuid4()}/revoke")
    assert unknown_key.status_code == 404
    assert unknown_key.json()["detail"] == "key_not_found"

    events = _load_events(database_url)
    list_events = [event for event in events if event.action == "admin.employee_key:list"]
    revoke_events = [event for event in events if event.action == "admin.employee_key:revoke"]

    assert any(event.result == "success" for event in list_events)
    assert any(event.result == "success" for event in revoke_events)
    assert any(
        event.result == "failure" and event.reason == "key_already_revoked"
        for event in revoke_events
    )
    assert any(
        event.result == "failure" and event.reason == "key_already_used"
        for event in revoke_events
    )
    assert any(
        event.result == "failure" and event.reason == "key_already_expired"
        for event in revoke_events
    )
    assert any(
        event.result == "failure" and event.reason == "key_not_found"
        for event in revoke_events
    )
