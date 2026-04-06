"""Unit tests for compensation service workflows."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.models.base import Base
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.finance.dao.bonus_entry_dao import BonusEntryDAO
from hrm_backend.finance.dao.compensation_raise_confirmation_dao import (
    CompensationRaiseConfirmationDAO,
)
from hrm_backend.finance.dao.compensation_raise_request_dao import (
    CompensationRaiseRequestDAO,
)
from hrm_backend.finance.dao.salary_band_dao import SalaryBandDAO
from hrm_backend.finance.schemas.compensation import (
    BonusUpsertRequest,
    CompensationRaiseCreateRequest,
    CompensationRaiseDecisionRequest,
    SalaryBandCreateRequest,
)
from hrm_backend.finance.services.compensation_service import (
    RAISE_EFFECTIVE_DATE_BACKDATED,
    CompensationService,
)
from hrm_backend.finance.utils.money import CURRENCY_CODE
from hrm_backend.settings import AppSettings
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.models.vacancy import Vacancy


class _AuditServiceStub(AuditService):
    """Audit service double that captures API events in memory."""

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_api_event(self, **kwargs) -> None:  # type: ignore[override]
        self.events.append(kwargs)


def _build_request(path: str) -> Request:
    """Create minimal request object for service calls."""
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 8000),
        }
    )


def _auth_context(role: str, subject_id: str) -> AuthContext:
    """Build deterministic auth context for tests."""
    return AuthContext(
        subject_id=UUID(subject_id),
        role=role,
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )


def _seed_employee(
    session: Session,
    *,
    vacancy_id: str,
    employee_id: str,
    manager_staff_id: str,
) -> None:
    """Insert vacancy and employee profile fixtures."""
    session.add(
        Vacancy(
            vacancy_id=vacancy_id,
            title="Engineer",
            description="Build platform",
            department="Engineering",
            status="open",
            hiring_manager_staff_id=manager_staff_id,
        )
    )
    session.add(
        EmployeeProfile(
            employee_id=employee_id,
            hire_conversion_id=str(uuid4()),
            vacancy_id=vacancy_id,
            candidate_id=str(uuid4()),
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            phone=None,
            location="Minsk",
            current_title="Engineer",
            extra_data_json={},
            offer_terms_summary="Offer summary",
            start_date=datetime(2026, 4, 1, tzinfo=UTC).date(),
            created_by_staff_id="hr-1",
        )
    )
    session.commit()


def _build_service(session: Session, audit_service: AuditService) -> CompensationService:
    """Construct compensation service with SQLite-backed DAOs."""
    settings = AppSettings(
        database_url="sqlite+pysqlite:///:memory:",
        redis_url="redis://localhost:6379/15",
        jwt_secret="unit-test-secret-with-minimum-32-bytes",
        compensation_raise_manager_quorum=2,
    )
    return CompensationService(
        settings=settings,
        session=session,
        raise_request_dao=CompensationRaiseRequestDAO(session=session),
        confirmation_dao=CompensationRaiseConfirmationDAO(session=session),
        salary_band_dao=SalaryBandDAO(session=session),
        bonus_entry_dao=BonusEntryDAO(session=session),
        employee_profile_dao=EmployeeProfileDAO(session=session),
        vacancy_dao=VacancyDAO(session=session),
        audit_service=audit_service,
    )


def test_raise_request_rejects_backdated_effective_date() -> None:
    """Ensure backdated effective dates are rejected fail-closed."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    audit_service = _AuditServiceStub()
    with Session(engine) as session:
        _seed_employee(
            session,
            vacancy_id="00000000-0000-0000-0000-000000000101",
            employee_id="00000000-0000-0000-0000-000000000001",
            manager_staff_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        )
        service = _build_service(session, audit_service)

        with pytest.raises(HTTPException) as exc_info:
            service.create_raise_request(
                payload=CompensationRaiseCreateRequest(
                    employee_id=UUID("00000000-0000-0000-0000-000000000001"),
                    proposed_base_salary=2500.0,
                    effective_date=date.today() - timedelta(days=1),
                ),
                auth_context=_auth_context(
                    role="manager",
                    subject_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                ),
                request=_build_request("/api/v1/compensation/raises"),
            )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == RAISE_EFFECTIVE_DATE_BACKDATED
    assert audit_service.events[-1]["reason"] == RAISE_EFFECTIVE_DATE_BACKDATED


def test_raise_request_quorum_and_leader_approval() -> None:
    """Verify confirmation quorum transitions to leader approval."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    audit_service = _AuditServiceStub()
    with Session(engine) as session:
        _seed_employee(
            session,
            vacancy_id="00000000-0000-0000-0000-000000000102",
            employee_id="00000000-0000-0000-0000-000000000002",
            manager_staff_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        )
        service = _build_service(session, audit_service)
        request_payload = CompensationRaiseCreateRequest(
            employee_id=UUID("00000000-0000-0000-0000-000000000002"),
            proposed_base_salary=3000.5,
            effective_date=date.today(),
        )
        created = service.create_raise_request(
            payload=request_payload,
            auth_context=_auth_context(
                role="manager",
                subject_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            ),
            request=_build_request("/api/v1/compensation/raises"),
        )

        confirmed = service.confirm_raise_request(
            request_id=str(created.request_id),
            auth_context=_auth_context(
                role="manager",
                subject_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            ),
            request=_build_request("/api/v1/compensation/raises/confirm"),
        )
        assert confirmed.confirmation_count == 1
        assert confirmed.status == "pending_confirmations"

        confirmed = service.confirm_raise_request(
            request_id=str(created.request_id),
            auth_context=_auth_context(
                role="manager",
                subject_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            ),
            request=_build_request("/api/v1/compensation/raises/confirm"),
        )
        assert confirmed.confirmation_count == 2
        assert confirmed.status == "awaiting_leader"

        approved = service.approve_raise_request(
            request_id=str(created.request_id),
            payload=CompensationRaiseDecisionRequest(note="Approved"),
            auth_context=_auth_context(
                role="leader",
                subject_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            ),
            request=_build_request("/api/v1/compensation/raises/approve"),
        )
        assert approved.status == "approved"
        assert approved.currency == CURRENCY_CODE


def test_salary_band_create_and_list() -> None:
    """Verify HR can create and list salary bands."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    audit_service = _AuditServiceStub()
    with Session(engine) as session:
        _seed_employee(
            session,
            vacancy_id="00000000-0000-0000-0000-000000000103",
            employee_id="00000000-0000-0000-0000-000000000003",
            manager_staff_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        )
        service = _build_service(session, audit_service)

        created = service.create_salary_band(
            payload=SalaryBandCreateRequest(
                vacancy_id=UUID("00000000-0000-0000-0000-000000000103"),
                min_amount=1500.0,
                max_amount=2500.0,
            ),
            auth_context=_auth_context(
                role="hr",
                subject_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            ),
            request=_build_request("/api/v1/compensation/salary-bands"),
        )
        assert created.currency == CURRENCY_CODE
        history = service.list_salary_bands(vacancy_id=str(created.vacancy_id))
        assert len(history.items) == 1


def test_compensation_table_rows_include_bonus_and_band_alignment() -> None:
    """Verify compensation table aggregates raise, bonus, and band data."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    audit_service = _AuditServiceStub()
    with Session(engine) as session:
        _seed_employee(
            session,
            vacancy_id="00000000-0000-0000-0000-000000000104",
            employee_id="00000000-0000-0000-0000-000000000004",
            manager_staff_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        )
        service = _build_service(session, audit_service)

        service.create_salary_band(
            payload=SalaryBandCreateRequest(
                vacancy_id=UUID("00000000-0000-0000-0000-000000000104"),
                min_amount=1000.0,
                max_amount=2000.0,
            ),
            auth_context=_auth_context(
                role="hr",
                subject_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            ),
            request=_build_request("/api/v1/compensation/salary-bands"),
        )

        raise_request = service.create_raise_request(
            payload=CompensationRaiseCreateRequest(
                employee_id=UUID("00000000-0000-0000-0000-000000000004"),
                proposed_base_salary=1800.0,
                effective_date=date.today(),
            ),
            auth_context=_auth_context(
                role="manager",
                subject_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            ),
            request=_build_request("/api/v1/compensation/raises"),
        )
        service.confirm_raise_request(
            request_id=str(raise_request.request_id),
            auth_context=_auth_context(
                role="manager",
                subject_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            ),
            request=_build_request("/api/v1/compensation/raises/confirm"),
        )
        service.confirm_raise_request(
            request_id=str(raise_request.request_id),
            auth_context=_auth_context(
                role="manager",
                subject_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            ),
            request=_build_request("/api/v1/compensation/raises/confirm"),
        )
        service.approve_raise_request(
            request_id=str(raise_request.request_id),
            payload=CompensationRaiseDecisionRequest(note=None),
            auth_context=_auth_context(
                role="leader",
                subject_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
            ),
            request=_build_request("/api/v1/compensation/raises/approve"),
        )

        service.upsert_bonus_entry(
            payload=BonusUpsertRequest(
                employee_id=UUID("00000000-0000-0000-0000-000000000004"),
                period_month=date(2026, 4, 1),
                amount=500.0,
                note="Quarterly bonus",
            ),
            auth_context=_auth_context(
                role="accountant",
                subject_id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
            ),
            request=_build_request("/api/v1/compensation/bonuses"),
        )

        response = service.list_compensation_table(
            auth_context=_auth_context(
                role="hr",
                subject_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            ),
            request=_build_request("/api/v1/compensation/table"),
            limit=20,
            offset=0,
        )

    assert response.total == 1
    row = response.items[0]
    assert row.currency == CURRENCY_CODE
    assert row.base_salary == 1800.0
    assert row.bonus_amount == 500.0
    assert row.band_alignment_status == "within_band"
