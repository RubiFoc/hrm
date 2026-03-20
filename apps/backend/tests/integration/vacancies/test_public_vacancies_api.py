"""Integration tests for the public vacancy board API."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.models.vacancy import Vacancy

pytestmark = pytest.mark.anyio


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for public vacancy list tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'public_vacancies.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for public vacancy list tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
    )

    def _get_settings_override() -> AppSettings:
        return settings

    app.dependency_overrides[get_settings] = _get_settings_override

    engine = create_engine(sqlite_database_url, future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Vacancy(
                    vacancy_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                    title="Senior Python Engineer",
                    description="Build public APIs and internal tooling.",
                    department="Engineering",
                    status="open",
                    created_at=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 3, 12, 8, 30, tzinfo=UTC),
                ),
                Vacancy(
                    vacancy_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                    title="Recruiter",
                    description="Keep hiring pipelines healthy.",
                    department="People",
                    status="paused",
                    created_at=datetime(2026, 3, 9, 8, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 3, 11, 8, 30, tzinfo=UTC),
                ),
                Vacancy(
                    vacancy_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                    title="Data Analyst",
                    description="Own reporting quality and dashboards.",
                    department="Analytics",
                    status="OPEN",
                    created_at=datetime(2026, 3, 11, 8, 0, tzinfo=UTC),
                    updated_at=datetime(2026, 3, 13, 8, 30, tzinfo=UTC),
                ),
            ]
        )
        session.commit()

    try:
        yield app, sqlite_database_url
    finally:
        app.dependency_overrides.pop(get_settings, None)
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for public vacancy list tests."""
    configured, _ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_public_vacancies_api_lists_open_roles_only(api_client: AsyncClient) -> None:
    """Verify public endpoint returns open vacancies without staff-only fields."""
    response = await api_client.get("/api/v1/public/vacancies")

    assert response.status_code == 200
    payload = response.json()
    assert [item["title"] for item in payload["items"]] == [
        "Data Analyst",
        "Senior Python Engineer",
    ]
    assert all("hiring_manager_login" not in item for item in payload["items"])
    assert all("hiring_manager_staff_id" not in item for item in payload["items"])
