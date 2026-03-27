"""Integration tests for employee referral API."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dependencies.candidates import get_candidate_storage
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy

pytestmark = pytest.mark.anyio


class InMemoryCandidateStorage:
    """In-memory object storage replacement for integration tests."""

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
    return f"sqlite+pysqlite:///{tmp_path / 'referrals_api.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for referral integration tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
        cv_max_size_bytes=1024,
    )
    storage = InMemoryCandidateStorage()
    context_holder = {
        "context": AuthContext(
            subject_id=uuid4(),
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

    def _get_storage_override() -> InMemoryCandidateStorage:
        return storage

    app.dependency_overrides[get_settings] = _get_settings_override
    app.dependency_overrides[get_current_auth_context] = _get_auth_context_override
    app.dependency_overrides[get_candidate_storage] = _get_storage_override

    engine = create_engine(sqlite_database_url, future=True)
    Base.metadata.create_all(engine)
    seeded = _seed_referral_context(sqlite_database_url)
    context_holder["context"] = AuthContext(
        subject_id=seeded["employee_staff_ids"][0],
        role="employee",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    try:
        yield app, context_holder, sqlite_database_url, seeded
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_candidate_storage, None)
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for referral integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


async def test_referral_submit_and_duplicate_merge(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify duplicate referrals are merged and keep the original bonus owner."""
    _, context_holder, _, seeded = configured_app
    vacancy_id = seeded["vacancy_id"]
    first_staff_id = seeded["employee_staff_ids"][0]
    second_staff_id = seeded["employee_staff_ids"][1]

    context_holder["context"] = AuthContext(
        subject_id=first_staff_id,
        role="employee",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    first_response = await _submit_referral(
        api_client,
        vacancy_id=vacancy_id,
        email="referral@example.com",
        cv_seed="first",
    )
    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload["is_duplicate"] is False
    assert first_payload["bonus_owner_employee_id"] == seeded["employee_ids"][first_staff_id]

    context_holder["context"] = AuthContext(
        subject_id=second_staff_id,
        role="employee",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    second_response = await _submit_referral(
        api_client,
        vacancy_id=vacancy_id,
        email="referral@example.com",
        cv_seed="second",
    )
    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["is_duplicate"] is True
    assert second_payload["referral_id"] == first_payload["referral_id"]
    assert second_payload["bonus_owner_employee_id"] == seeded["employee_ids"][first_staff_id]


async def test_referral_review_rejects_forbidden_manager(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify managers cannot review referrals outside their vacancy scope."""
    _, context_holder, _, seeded = configured_app
    vacancy_id = seeded["vacancy_id"]

    context_holder["context"] = AuthContext(
        subject_id=seeded["employee_staff_ids"][0],
        role="employee",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    response = await _submit_referral(
        api_client,
        vacancy_id=vacancy_id,
        email="forbidden@example.com",
        cv_seed="forbidden",
    )
    referral_id = response.json()["referral_id"]

    context_holder["context"] = AuthContext(
        subject_id=seeded["other_manager_staff_id"],
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    denied = await api_client.post(
        f"/api/v1/referrals/{referral_id}/review",
        json={"to_stage": "screening"},
    )
    assert denied.status_code == 403


async def test_referral_review_rejects_disallowed_stage(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify referral review only allows screening or shortlist transitions."""
    _, context_holder, _, seeded = configured_app
    vacancy_id = seeded["vacancy_id"]

    context_holder["context"] = AuthContext(
        subject_id=seeded["employee_staff_ids"][0],
        role="employee",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    response = await _submit_referral(
        api_client,
        vacancy_id=vacancy_id,
        email="stage@example.com",
        cv_seed="stage",
    )
    referral_id = response.json()["referral_id"]

    context_holder["context"] = AuthContext(
        subject_id=seeded["hr_staff_id"],
        role="hr",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )
    invalid = await api_client.post(
        f"/api/v1/referrals/{referral_id}/review",
        json={"to_stage": "offer"},
    )
    assert invalid.status_code == 422


async def _submit_referral(
    api_client: AsyncClient,
    *,
    vacancy_id: str,
    email: str,
    cv_seed: str,
) -> Response:
    content = f"referral-cv-{cv_seed}".encode()
    checksum = hashlib.sha256(content).hexdigest()
    return await api_client.post(
        "/api/v1/referrals",
        data={
            "vacancy_id": vacancy_id,
            "full_name": "Ada Lovelace",
            "phone": "+375291112233",
            "email": email,
            "checksum_sha256": checksum,
        },
        files={"file": ("cv.pdf", content, "application/pdf")},
    )


def _seed_referral_context(database_url: str) -> dict[str, object]:
    engine = create_engine(database_url, future=True)
    vacancy_id = str(uuid4())
    manager_staff_id = str(uuid4())
    other_manager_staff_id = str(uuid4())
    hr_staff_id = str(uuid4())
    employee_staff_ids = [str(uuid4()), str(uuid4())]
    employee_ids: dict[str, str] = {}
    try:
        with Session(engine) as session:
            session.add(
                Vacancy(
                    vacancy_id=vacancy_id,
                    title="Referral Vacancy",
                    description="Referral pipeline",
                    department="Engineering",
                    status="open",
                    hiring_manager_staff_id=manager_staff_id,
                )
            )
            session.add_all(
                [
                    StaffAccount(
                        staff_id=manager_staff_id,
                        login="manager-1",
                        email="manager1@example.com",
                        password_hash="hash",
                        role="manager",
                        is_active=True,
                    ),
                    StaffAccount(
                        staff_id=other_manager_staff_id,
                        login="manager-2",
                        email="manager2@example.com",
                        password_hash="hash",
                        role="manager",
                        is_active=True,
                    ),
                    StaffAccount(
                        staff_id=hr_staff_id,
                        login="hr-1",
                        email="hr1@example.com",
                        password_hash="hash",
                        role="hr",
                        is_active=True,
                    ),
                ]
            )
            for index, staff_id in enumerate(employee_staff_ids, start=1):
                session.add(
                    StaffAccount(
                        staff_id=staff_id,
                        login=f"employee-{index}",
                        email=f"employee{index}@example.com",
                        password_hash="hash",
                        role="employee",
                        is_active=True,
                    )
                )
                employee_id = _seed_employee_profile(
                    session=session,
                    vacancy_id=vacancy_id,
                    staff_id=staff_id,
                    created_by_staff_id=hr_staff_id,
                    suffix=str(index),
                )
                employee_ids[staff_id] = employee_id

            session.commit()
    finally:
        engine.dispose()

    return {
        "vacancy_id": vacancy_id,
        "manager_staff_id": manager_staff_id,
        "other_manager_staff_id": other_manager_staff_id,
        "hr_staff_id": hr_staff_id,
        "employee_staff_ids": employee_staff_ids,
        "employee_ids": employee_ids,
    }


def _seed_employee_profile(
    *,
    session: Session,
    vacancy_id: str,
    staff_id: str,
    created_by_staff_id: str,
    suffix: str,
) -> str:
    candidate_id = str(uuid4())
    offer_id = str(uuid4())
    transition_id = str(uuid4())
    conversion_id = str(uuid4())
    employee_id = str(uuid4())

    session.add(
        CandidateProfile(
            candidate_id=candidate_id,
            owner_subject_id=f"seed-{suffix}",
            first_name=f"Employee{suffix}",
            last_name="Seed",
            email=f"employee{suffix}@example.com",
            phone="+375291000000",
            location=None,
            current_title="Engineer",
            extra_data={},
        )
    )
    session.add(
        Offer(
            offer_id=offer_id,
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            status="accepted",
        )
    )
    session.add(
        PipelineTransition(
            transition_id=transition_id,
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            from_stage="offer",
            to_stage="hired",
            reason="seed",
            changed_by_sub=created_by_staff_id,
            changed_by_role="hr",
            transitioned_at=datetime.now(UTC),
        )
    )
    session.add(
        HireConversion(
            conversion_id=conversion_id,
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            offer_id=offer_id,
            hired_transition_id=transition_id,
            status="ready",
            candidate_snapshot_json={
                "first_name": f"Employee{suffix}",
                "last_name": "Seed",
                "email": f"employee{suffix}@example.com",
            },
            offer_snapshot_json={"status": "accepted"},
            converted_at=datetime.now(UTC),
            converted_by_staff_id=created_by_staff_id,
        )
    )
    session.add(
        EmployeeProfile(
            employee_id=employee_id,
            hire_conversion_id=conversion_id,
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            first_name=f"Employee{suffix}",
            last_name="Seed",
            email=f"employee{suffix}@example.com",
            phone="+375291000000",
            location=None,
            current_title="Engineer",
            extra_data_json={},
            offer_terms_summary=None,
            start_date=None,
            staff_account_id=staff_id,
            created_by_staff_id=created_by_staff_id,
        )
    )
    return employee_id
