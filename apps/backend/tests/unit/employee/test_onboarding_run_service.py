"""Unit tests for onboarding-start payload mapping and persistence rules."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.employee.dao.onboarding_run_dao import OnboardingRunDAO
from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.models.onboarding import OnboardingRun
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.services.onboarding_service import OnboardingRunService
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy


def _seed_bootstrapped_employee(session: Session) -> EmployeeProfile:
    """Insert one employee profile and its source handoff rows for onboarding tests."""
    vacancy_id = "11111111-1111-4111-8111-111111111111"
    candidate_id = "22222222-2222-4222-8222-222222222222"
    offer_id = "33333333-3333-4333-8333-333333333333"
    transition_id = "44444444-4444-4444-8444-444444444444"
    conversion_id = "55555555-5555-4555-8555-555555555555"
    employee_id = "66666666-6666-4666-8666-666666666666"

    session.add(
        Vacancy(
            vacancy_id=vacancy_id,
            title="HRIS Engineer",
            description="Build HR workflows",
            department="Engineering",
            status="open",
        )
    )
    session.add(
        CandidateProfile(
            candidate_id=candidate_id,
            owner_subject_id="candidate-owner",
            first_name="Ada",
            last_name="Lovelace",
            email="ada@example.com",
            phone="+375291234567",
            location="Minsk",
            current_title="Backend Engineer",
            extra_data={"languages": ["ru", "en"]},
        )
    )
    session.add(
        Offer(
            offer_id=offer_id,
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            status="accepted",
            terms_summary="Base salary 5000 BYN gross.",
            proposed_start_date=date(2026, 4, 1),
            expires_at=date(2026, 3, 20),
            note="Manual delivery by HR.",
            sent_at=datetime(2026, 3, 10, 10, 30, tzinfo=UTC),
            sent_by_staff_id="77777777-7777-4777-8777-777777777777",
            decision_at=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
            decision_note="Accepted by phone.",
            decision_recorded_by_staff_id="88888888-8888-4888-8888-888888888888",
        )
    )
    session.add(
        PipelineTransition(
            transition_id=transition_id,
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            from_stage="offer",
            to_stage="hired",
            reason="accepted_offer",
            changed_by_sub="99999999-9999-4999-8999-999999999999",
            changed_by_role="hr",
            transitioned_at=datetime(2026, 3, 10, 12, 5, tzinfo=UTC),
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
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.com",
                "phone": "+375291234567",
                "location": "Minsk",
                "current_title": "Backend Engineer",
                "extra_data": {"languages": ["ru", "en"]},
            },
            offer_snapshot_json={
                "status": "accepted",
                "terms_summary": "Base salary 5000 BYN gross.",
                "proposed_start_date": "2026-04-01",
            },
            converted_at=datetime(2026, 3, 10, 12, 5, tzinfo=UTC),
            converted_by_staff_id="99999999-9999-4999-8999-999999999999",
        )
    )
    employee = EmployeeProfile(
        employee_id=employee_id,
        hire_conversion_id=conversion_id,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+375291234567",
        location="Minsk",
        current_title="Backend Engineer",
        extra_data_json={"languages": ["ru", "en"]},
        offer_terms_summary="Base salary 5000 BYN gross.",
        start_date=date(2026, 4, 1),
        created_by_staff_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def test_build_create_payload_maps_employee_profile_to_started_onboarding_run() -> None:
    """Verify onboarding payload is built deterministically from employee-profile state."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            employee = _seed_bootstrapped_employee(session)
            service = OnboardingRunService(dao=OnboardingRunDAO(session=session))

            payload = service.build_create_payload(
                employee_profile=employee,
                started_by_staff_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            )

            assert str(payload.employee_id) == employee.employee_id
            assert str(payload.hire_conversion_id) == employee.hire_conversion_id
            assert payload.status == "started"
            assert str(payload.started_by_staff_id) == "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    finally:
        engine.dispose()


def test_onboarding_run_persistence_enforces_one_run_per_employee() -> None:
    """Verify the onboarding table rejects a second run for the same employee profile."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            employee = _seed_bootstrapped_employee(session)
            dao = OnboardingRunDAO(session=session)
            service = OnboardingRunService(dao=dao)
            payload = service.build_create_payload(
                employee_profile=employee,
                started_by_staff_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            )

            dao.create_run(payload=payload)

            with pytest.raises(IntegrityError):
                dao.create_run(payload=payload)
            session.rollback()

            rows = list(
                session.execute(
                    select(OnboardingRun).order_by(
                        OnboardingRun.started_at,
                        OnboardingRun.onboarding_id,
                    )
                ).scalars()
            )
            assert len(rows) == 1
            assert rows[0].employee_id == employee.employee_id
    finally:
        engine.dispose()
