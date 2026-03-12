"""Unit tests for atomic hire-conversion persistence on pipeline transitions."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import Request
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.interviews.dao.feedback_dao import InterviewFeedbackDAO
from hrm_backend.interviews.dao.interview_dao import InterviewDAO
from hrm_backend.vacancies.dao.offer_dao import OfferDAO
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy
from hrm_backend.vacancies.schemas.pipeline import PipelineTransitionCreateRequest
from hrm_backend.vacancies.services.vacancy_service import VacancyService


class _FailingHireConversionService:
    """Deterministic test double that fails before the transaction is committed."""

    def create_ready_handoff(self, **_: object) -> None:
        raise RuntimeError("deterministic hire conversion failure")


class _FakeAuditService:
    """Minimal audit double for vacancy service tests."""

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_api_event(self, **payload: object) -> None:
        self.events.append(payload)


def _build_request() -> Request:
    """Create a minimal request object for service-level tests."""
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/pipeline/transitions",
            "headers": [],
        }
    )
    request.state.request_id = "unit-test-request"
    return request


def test_hired_transition_rolls_back_when_handoff_persistence_fails(tmp_path: Path) -> None:
    """Verify no `hired` transition is committed when handoff persistence raises."""
    database_url = f"sqlite+pysqlite:///{tmp_path / 'hire_conversion_atomicity.db'}"
    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)

    vacancy_id = "11111111-1111-4111-8111-111111111111"
    candidate_id = "22222222-2222-4222-8222-222222222222"
    offer_id = "33333333-3333-4333-8333-333333333333"

    with Session(engine) as session:
        session.add(
            Vacancy(
                vacancy_id=vacancy_id,
                title="HRIS Engineer",
                description="Build hiring workflows",
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
                phone=None,
                location=None,
                current_title="Backend Engineer",
                extra_data={},
            )
        )
        session.add(
            PipelineTransition(
                vacancy_id=vacancy_id,
                candidate_id=candidate_id,
                from_stage=None,
                to_stage="offer",
                reason="seed_offer_stage",
                changed_by_sub="44444444-4444-4444-8444-444444444444",
                changed_by_role="hr",
                transitioned_at=datetime(2026, 3, 10, 11, 0, tzinfo=UTC),
            )
        )
        session.add(
            Offer(
                offer_id=offer_id,
                vacancy_id=vacancy_id,
                candidate_id=candidate_id,
                status="accepted",
                terms_summary="Base salary 5000 BYN gross.",
                sent_at=datetime(2026, 3, 10, 10, 30, tzinfo=UTC),
                sent_by_staff_id="44444444-4444-4444-8444-444444444444",
                decision_at=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
                decision_note="Candidate accepted by phone.",
                decision_recorded_by_staff_id="44444444-4444-4444-8444-444444444444",
            )
        )
        session.commit()

    with Session(engine) as session:
        service = VacancyService(
            session=session,
            vacancy_dao=VacancyDAO(session=session),
            transition_dao=PipelineTransitionDAO(session=session),
            offer_dao=OfferDAO(session=session),
            candidate_profile_dao=CandidateProfileDAO(session=session),
            interview_dao=InterviewDAO(session=session),
            interview_feedback_dao=InterviewFeedbackDAO(session=session),
            staff_account_dao=StaffAccountDAO(session=session),
            hire_conversion_service=_FailingHireConversionService(),  # type: ignore[arg-type]
            audit_service=_FakeAuditService(),  # type: ignore[arg-type]
        )

        with pytest.raises(RuntimeError, match="deterministic hire conversion failure"):
            service.transition_pipeline(
                payload=PipelineTransitionCreateRequest(
                    vacancy_id=vacancy_id,
                    candidate_id=candidate_id,
                    to_stage="hired",
                    reason="accepted_offer",
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
        transitions = list(
            session.execute(
                select(PipelineTransition).order_by(
                    PipelineTransition.transitioned_at.asc(),
                    PipelineTransition.transition_id.asc(),
                )
            ).scalars()
        )
        assert [transition.to_stage for transition in transitions] == ["offer"]

    engine.dispose()
