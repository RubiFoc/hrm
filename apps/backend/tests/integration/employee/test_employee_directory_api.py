"""Integration tests for employee directory visibility and avatar APIs."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.employee.dependencies.employee import get_employee_avatar_storage
from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy

pytestmark = pytest.mark.anyio


class InMemoryEmployeeAvatarStorage:
    """In-memory object-storage replacement for avatar integration tests."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def put_object(
        self,
        *,
        object_key: str,
        data: bytes,
        mime_type: str,
        enable_sse: bool,
    ) -> None:
        del mime_type, enable_sse
        self._store[object_key] = data

    def get_object(self, *, object_key: str) -> bytes:
        return self._store[object_key]


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'employee_directory_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for employee directory integration tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
    )
    avatar_storage = InMemoryEmployeeAvatarStorage()
    staff_id = uuid4()
    context_holder = {
        "context": AuthContext(
            subject_id=staff_id,
            role="employee",
            session_id=uuid4(),
            token_id=uuid4(),
            expires_at=9999999999,
        )
    }

    def _get_settings_override() -> AppSettings:
        return settings

    def _get_auth_context_override() -> AuthContext:
        return context_holder["context"]

    def _get_storage_override() -> InMemoryEmployeeAvatarStorage:
        return avatar_storage

    app.dependency_overrides[get_settings] = _get_settings_override
    app.dependency_overrides[get_current_auth_context] = _get_auth_context_override
    app.dependency_overrides[get_employee_avatar_storage] = _get_storage_override

    engine = create_engine(sqlite_database_url, future=True)
    Base.metadata.create_all(engine)
    seeded = _seed_employee_profiles(
        sqlite_database_url=sqlite_database_url,
        actor_staff_id=str(staff_id),
    )
    try:
        yield app, context_holder, avatar_storage, seeded
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_employee_avatar_storage, None)
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for employee directory integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


def _seed_employee_profiles(
    *,
    sqlite_database_url: str,
    actor_staff_id: str,
) -> dict[str, str]:
    """Seed two employee profiles for directory and avatar endpoint checks."""
    engine = create_engine(sqlite_database_url, future=True)
    first_employee_id = str(uuid4())
    second_employee_id = str(uuid4())
    first_candidate_id = str(uuid4())
    second_candidate_id = str(uuid4())
    first_vacancy_id = str(uuid4())
    second_vacancy_id = str(uuid4())
    first_conversion_id = str(uuid4())
    second_conversion_id = str(uuid4())
    first_offer_id = str(uuid4())
    second_offer_id = str(uuid4())
    first_transition_id = str(uuid4())
    second_transition_id = str(uuid4())
    try:
        with Session(engine) as session:
            session.add(
                StaffAccount(
                    staff_id=actor_staff_id,
                    login="ada",
                    email="ada@example.com",
                    password_hash="hash",
                    role="employee",
                    is_active=True,
                )
            )
            session.add_all(
                [
                    Vacancy(
                        vacancy_id=first_vacancy_id,
                        title="Engineer",
                        description="Build internal systems",
                        department="Engineering",
                        status="open",
                    ),
                    Vacancy(
                        vacancy_id=second_vacancy_id,
                        title="HR Partner",
                        description="Support hiring operations",
                        department="HR",
                        status="open",
                    ),
                ]
            )
            session.add_all(
                [
                    CandidateProfile(
                        candidate_id=first_candidate_id,
                        owner_subject_id="owner-1",
                        first_name="Ada",
                        last_name="Lovelace",
                        email="ada@example.com",
                        phone="+375291111111",
                        location="Minsk",
                        current_title="Engineer",
                        extra_data={"department": "Engineering", "manager": "Grace Hopper"},
                    ),
                    CandidateProfile(
                        candidate_id=second_candidate_id,
                        owner_subject_id="owner-2",
                        first_name="Ivan",
                        last_name="Petrov",
                        email="ivan@example.com",
                        phone="+375292222222",
                        location="Grodno",
                        current_title="HR Partner",
                        extra_data={"department": "HR", "manager": "Natalia"},
                    ),
                ]
            )
            session.add_all(
                [
                    Offer(
                        offer_id=first_offer_id,
                        vacancy_id=first_vacancy_id,
                        candidate_id=first_candidate_id,
                        status="accepted",
                        terms_summary="Base salary 5000 BYN gross.",
                        proposed_start_date=date(2026, 4, 1),
                    ),
                    Offer(
                        offer_id=second_offer_id,
                        vacancy_id=second_vacancy_id,
                        candidate_id=second_candidate_id,
                        status="accepted",
                        terms_summary="Base salary 4200 BYN gross.",
                        proposed_start_date=date(2026, 4, 15),
                    ),
                ]
            )
            session.add_all(
                [
                    PipelineTransition(
                        transition_id=first_transition_id,
                        vacancy_id=first_vacancy_id,
                        candidate_id=first_candidate_id,
                        from_stage="offer",
                        to_stage="hired",
                        reason="accepted_offer",
                        changed_by_sub="seed",
                        changed_by_role="hr",
                        transitioned_at=datetime(2026, 3, 21, 9, 0, tzinfo=UTC),
                    ),
                    PipelineTransition(
                        transition_id=second_transition_id,
                        vacancy_id=second_vacancy_id,
                        candidate_id=second_candidate_id,
                        from_stage="offer",
                        to_stage="hired",
                        reason="accepted_offer",
                        changed_by_sub="seed",
                        changed_by_role="hr",
                        transitioned_at=datetime(2026, 3, 21, 9, 5, tzinfo=UTC),
                    ),
                ]
            )
            session.add_all(
                [
                    HireConversion(
                        conversion_id=first_conversion_id,
                        vacancy_id=first_vacancy_id,
                        candidate_id=first_candidate_id,
                        offer_id=first_offer_id,
                        hired_transition_id=first_transition_id,
                        status="ready",
                        candidate_snapshot_json={
                            "first_name": "Ada",
                            "last_name": "Lovelace",
                            "email": "ada@example.com",
                            "phone": "+375291111111",
                            "location": "Minsk",
                            "current_title": "Engineer",
                            "extra_data": {},
                        },
                        offer_snapshot_json={
                            "status": "accepted",
                            "terms_summary": "Base salary 5000 BYN gross.",
                            "proposed_start_date": "2026-04-01",
                        },
                        converted_at=datetime(2026, 3, 21, 9, 0, tzinfo=UTC),
                        converted_by_staff_id=str(uuid4()),
                    ),
                    HireConversion(
                        conversion_id=second_conversion_id,
                        vacancy_id=second_vacancy_id,
                        candidate_id=second_candidate_id,
                        offer_id=second_offer_id,
                        hired_transition_id=second_transition_id,
                        status="ready",
                        candidate_snapshot_json={
                            "first_name": "Ivan",
                            "last_name": "Petrov",
                            "email": "ivan@example.com",
                            "phone": "+375292222222",
                            "location": "Grodno",
                            "current_title": "HR Partner",
                            "extra_data": {},
                        },
                        offer_snapshot_json={
                            "status": "accepted",
                            "terms_summary": "Base salary 4200 BYN gross.",
                            "proposed_start_date": "2026-04-15",
                        },
                        converted_at=datetime(2026, 3, 21, 9, 5, tzinfo=UTC),
                        converted_by_staff_id=str(uuid4()),
                    ),
                ]
            )
            session.add_all(
                [
                    EmployeeProfile(
                        employee_id=first_employee_id,
                        hire_conversion_id=first_conversion_id,
                        vacancy_id=first_vacancy_id,
                        candidate_id=first_candidate_id,
                        first_name="Ada",
                        last_name="Lovelace",
                        email="ada@example.com",
                        phone="+375291111111",
                        location="Minsk",
                        current_title="Engineer",
                        extra_data_json={"department": "Engineering", "manager": "Grace Hopper"},
                        offer_terms_summary="Base salary 5000 BYN gross.",
                        start_date=date(2026, 4, 1),
                        staff_account_id=actor_staff_id,
                        created_by_staff_id=str(uuid4()),
                    ),
                    EmployeeProfile(
                        employee_id=second_employee_id,
                        hire_conversion_id=second_conversion_id,
                        vacancy_id=second_vacancy_id,
                        candidate_id=second_candidate_id,
                        first_name="Ivan",
                        last_name="Petrov",
                        email="ivan@example.com",
                        phone="+375292222222",
                        location="Grodno",
                        current_title="HR Partner",
                        extra_data_json={"department": "HR", "manager": "Natalia"},
                        offer_terms_summary="Base salary 4200 BYN gross.",
                        start_date=date(2026, 4, 15),
                        staff_account_id=None,
                        created_by_staff_id=str(uuid4()),
                    ),
                ]
            )
            session.commit()
    finally:
        engine.dispose()

    return {
        "self_employee_id": first_employee_id,
        "peer_employee_id": second_employee_id,
    }


async def test_employee_can_list_directory_and_read_profile(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify authenticated employee can view directory cards and detailed peer profile."""
    _, _, _, seeded = configured_app

    list_response = await api_client.get("/api/v1/employees/directory")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 2
    returned_ids = {item["employee_id"] for item in payload["items"]}
    assert seeded["self_employee_id"] in returned_ids
    assert seeded["peer_employee_id"] in returned_ids

    detail_response = await api_client.get(
        f"/api/v1/employees/directory/{seeded['peer_employee_id']}"
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["employee_id"] == seeded["peer_employee_id"]
    assert detail_payload["full_name"] == "Ivan Petrov"
    assert detail_payload["department"] == "HR"
    assert detail_payload["avatar_url"] is None


async def test_employee_can_upload_and_download_avatar(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify employee can upload own avatar and read avatar bytes by employee identifier."""
    _, _, _, seeded = configured_app
    avatar_bytes = b"\x89PNG\r\n\x1a\navatar"

    upload_response = await api_client.post(
        "/api/v1/employees/me/avatar",
        files={"file": ("avatar.png", avatar_bytes, "image/png")},
    )
    assert upload_response.status_code == 200
    upload_payload = upload_response.json()
    assert upload_payload["employee_id"] == seeded["self_employee_id"]
    assert upload_payload["avatar_url"].endswith(
        f"/api/v1/employees/{seeded['self_employee_id']}/avatar"
    )

    download_response = await api_client.get(
        f"/api/v1/employees/{seeded['self_employee_id']}/avatar"
    )
    assert download_response.status_code == 200
    assert download_response.content == avatar_bytes
    assert download_response.headers["Content-Type"].startswith("image/png")


async def test_hr_role_is_denied_for_employee_directory_reads(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify non-employee role cannot access employee directory read endpoints."""
    _, context_holder, _, _ = configured_app
    context_holder["context"] = context_holder["context"].model_copy(update={"role": "hr"})

    response = await api_client.get("/api/v1/employees/directory")
    assert response.status_code == 403
