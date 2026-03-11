"""Unit tests for atomic employee bootstrap, onboarding trigger, and task writes."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.dao.hire_conversion_dao import HireConversionDAO
from hrm_backend.employee.dao.onboarding_run_dao import OnboardingRunDAO
from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.schemas.profile import EmployeeProfileCreateRequest
from hrm_backend.employee.services.employee_profile_service import EmployeeProfileService
from hrm_backend.employee.services.onboarding_service import OnboardingRunService
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy


class _FailingOnboardingTaskService:
    """Task service double that fails after onboarding run creation and before commit."""

    def create_tasks_from_active_template(
        self,
        *,
        onboarding_run,
        commit: bool = True,
    ):
        """Raise deterministic failure while profile and onboarding rows remain uncommitted."""
        del onboarding_run, commit
        raise RuntimeError("deterministic onboarding task failure")


class _FakeAuditService:
    """Audit double used when atomicity, not audit persistence, is under test."""

    def record_api_event(self, **kwargs) -> None:
        """Ignore audit writes during atomicity tests."""
        del kwargs


def _build_request() -> Request:
    """Create minimal Starlette request object for service calls."""
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/employees",
            "headers": [],
            "client": ("127.0.0.1", 8000),
        }
    )


def _seed_ready_hire_conversion(session: Session) -> dict[str, str]:
    """Insert one ready hire conversion with upstream source rows."""
    vacancy_id = "11111111-1111-4111-8111-111111111111"
    candidate_id = "22222222-2222-4222-8222-222222222222"
    offer_id = "33333333-3333-4333-8333-333333333333"
    transition_id = "44444444-4444-4444-8444-444444444444"
    conversion_id = "55555555-5555-4555-8555-555555555555"

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
            sent_by_staff_id="66666666-6666-4666-8666-666666666666",
            decision_at=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
            decision_note="Accepted by phone.",
            decision_recorded_by_staff_id="77777777-7777-4777-8777-777777777777",
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
            changed_by_sub="88888888-8888-4888-8888-888888888888",
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
            converted_by_staff_id="88888888-8888-4888-8888-888888888888",
        )
    )
    session.commit()
    return {
        "vacancy_id": vacancy_id,
        "candidate_id": candidate_id,
    }


def test_employee_bootstrap_rolls_back_when_task_generation_fails(tmp_path: Path) -> None:
    """Verify no profile, onboarding run, or tasks remain when task generation raises."""
    database_url = f"sqlite+pysqlite:///{tmp_path / 'employee_onboarding_atomicity.db'}"
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            seeded = _seed_ready_hire_conversion(session)

        with Session(engine) as session:
            service = EmployeeProfileService(
                session=session,
                hire_conversion_dao=HireConversionDAO(session=session),
                profile_dao=EmployeeProfileDAO(session=session),
                onboarding_service=OnboardingRunService(dao=OnboardingRunDAO(session=session)),
                onboarding_task_service=_FailingOnboardingTaskService(),  # type: ignore[arg-type]
                audit_service=_FakeAuditService(),  # type: ignore[arg-type]
            )

            with pytest.raises(RuntimeError, match="deterministic onboarding task failure"):
                service.create_profile(
                    payload=EmployeeProfileCreateRequest(
                        vacancy_id=seeded["vacancy_id"],
                        candidate_id=seeded["candidate_id"],
                    ),
                    auth_context=AuthContext(
                        subject_id=uuid4(),
                        role="hr",
                        session_id=uuid4(),
                        token_id=uuid4(),
                        expires_at=9999999999,
                    ),
                    request=_build_request(),
                )

        with Session(engine) as session:
            assert list(session.execute(select(EmployeeProfile)).scalars()) == []
            assert list(session.execute(select(OnboardingRun)).scalars()) == []
            assert list(session.execute(select(OnboardingTask)).scalars()) == []
    finally:
        engine.dispose()
