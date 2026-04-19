"""Integration tests for department reference API routes."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for department integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'departments.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure application dependency overrides for department tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
    )
    context_holder = {"context": _make_context("admin")}

    def _get_settings_override() -> AppSettings:
        return settings

    def _get_auth_context_override() -> AuthContext:
        return context_holder["context"]

    app.dependency_overrides[get_settings] = _get_settings_override
    app.dependency_overrides[get_current_auth_context] = _get_auth_context_override

    engine = create_engine(sqlite_database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        yield app, context_holder
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide in-process async API client for department tests."""
    configured, _ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


def _make_context(role: str) -> AuthContext:
    return AuthContext(
        subject_id=uuid4(),
        role=role,
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )


async def _create_department(client: AsyncClient, *, name: str) -> dict[str, object]:
    response = await client.post("/api/v1/departments", json={"name": name})
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize(
    "role",
    ["admin", "hr", "manager", "employee", "leader", "accountant"],
)
async def test_departments_list_available_to_all_roles(
    configured_app,
    api_client: AsyncClient,
    role: str,
) -> None:
    """Ensure all staff roles can list departments."""
    _, context_holder = configured_app
    context_holder["context"] = _make_context("admin")
    created = await _create_department(api_client, name="Engineering")

    context_holder["context"] = _make_context(role)
    response = await api_client.get("/api/v1/departments", params={"limit": 20, "offset": 0})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert any(item["department_id"] == created["department_id"] for item in payload["items"])


@pytest.mark.parametrize(
    "role",
    ["admin", "hr", "manager", "employee", "leader", "accountant"],
)
async def test_departments_read_available_to_all_roles(
    configured_app,
    api_client: AsyncClient,
    role: str,
) -> None:
    """Ensure all staff roles can read department details."""
    _, context_holder = configured_app
    context_holder["context"] = _make_context("admin")
    created = await _create_department(api_client, name="People Ops")

    context_holder["context"] = _make_context(role)
    response = await api_client.get(f"/api/v1/departments/{created['department_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["department_id"] == created["department_id"]
    assert payload["name"] == "People Ops"


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        ("admin", 200),
        ("leader", 200),
        ("hr", 403),
        ("manager", 403),
        ("employee", 403),
        ("accountant", 403),
    ],
)
async def test_departments_create_requires_privileged_roles(
    configured_app,
    api_client: AsyncClient,
    role: str,
    expected_status: int,
) -> None:
    """Ensure only admin/leader can create departments."""
    _, context_holder = configured_app
    context_holder["context"] = _make_context(role)

    response = await api_client.post(
        "/api/v1/departments",
        json={"name": f"Dept {role}"},
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        ("admin", 200),
        ("leader", 200),
        ("hr", 403),
        ("manager", 403),
        ("employee", 403),
        ("accountant", 403),
    ],
)
async def test_departments_update_requires_privileged_roles(
    configured_app,
    api_client: AsyncClient,
    role: str,
    expected_status: int,
) -> None:
    """Ensure only admin/leader can update departments."""
    _, context_holder = configured_app
    context_holder["context"] = _make_context("admin")
    created = await _create_department(api_client, name="Operations")

    context_holder["context"] = _make_context(role)
    response = await api_client.patch(
        f"/api/v1/departments/{created['department_id']}",
        json={"name": f"Operations {role}"},
    )

    assert response.status_code == expected_status
