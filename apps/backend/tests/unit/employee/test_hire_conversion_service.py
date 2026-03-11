"""Unit tests for durable hire-conversion handoff payload building."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.employee.services.hire_conversion_service import HireConversionService
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition


class _UnusedDAO:
    """DAO double used when only payload construction is under test."""

    def create_conversion(self, **_: object):  # pragma: no cover - defensive only
        raise AssertionError("Persistence should not be called in payload-only tests")


def test_build_create_payload_returns_deterministic_candidate_and_offer_snapshots() -> None:
    """Verify payload builder freezes candidate and accepted-offer fields deterministically."""
    service = HireConversionService(dao=_UnusedDAO())  # type: ignore[arg-type]
    candidate = CandidateProfile(
        candidate_id="11111111-1111-4111-8111-111111111111",
        owner_subject_id="candidate-owner",
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="+375291234567",
        location="Minsk",
        current_title="Backend Engineer",
        extra_data={"languages": ["ru", "en"]},
    )
    offer = Offer(
        offer_id="22222222-2222-4222-8222-222222222222",
        vacancy_id="33333333-3333-4333-8333-333333333333",
        candidate_id=candidate.candidate_id,
        status="accepted",
        terms_summary="Base salary 5000 BYN gross.",
        proposed_start_date=date(2026, 4, 1),
        expires_at=date(2026, 3, 20),
        note="Manual delivery by HR.",
        sent_at=datetime(2026, 3, 10, 10, 30, tzinfo=UTC),
        sent_by_staff_id="44444444-4444-4444-8444-444444444444",
        decision_at=datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
        decision_note="Candidate accepted by phone.",
        decision_recorded_by_staff_id="55555555-5555-4555-8555-555555555555",
    )
    transition = PipelineTransition(
        transition_id="66666666-6666-4666-8666-666666666666",
        vacancy_id=offer.vacancy_id,
        candidate_id=candidate.candidate_id,
        from_stage="offer",
        to_stage="hired",
        reason="accepted_offer",
        changed_by_sub="77777777-7777-4777-8777-777777777777",
        changed_by_role="hr",
        transitioned_at=datetime(2026, 3, 10, 12, 5, tzinfo=UTC),
    )

    payload = service.build_create_payload(
        candidate=candidate,
        offer=offer,
        hired_transition=transition,
        converted_by_staff_id="77777777-7777-4777-8777-777777777777",
    )

    assert str(payload.vacancy_id) == offer.vacancy_id
    assert str(payload.offer_id) == offer.offer_id
    assert str(payload.hired_transition_id) == transition.transition_id
    assert payload.status == "ready"
    assert payload.candidate_snapshot.model_dump() == {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "phone": "+375291234567",
        "location": "Minsk",
        "current_title": "Backend Engineer",
        "extra_data": {"languages": ["ru", "en"]},
    }
    assert payload.offer_snapshot.model_dump(mode="json") == {
        "status": "accepted",
        "terms_summary": "Base salary 5000 BYN gross.",
        "proposed_start_date": "2026-04-01",
        "expires_at": "2026-03-20",
        "note": "Manual delivery by HR.",
        "sent_at": "2026-03-10T10:30:00Z",
        "sent_by_staff_id": "44444444-4444-4444-8444-444444444444",
        "decision_at": "2026-03-10T12:00:00Z",
        "decision_note": "Candidate accepted by phone.",
        "decision_recorded_by_staff_id": "55555555-5555-4555-8555-555555555555",
    }


def test_build_create_payload_rejects_non_accepted_offer() -> None:
    """Verify builder refuses to freeze a handoff from a non-accepted offer."""
    service = HireConversionService(dao=_UnusedDAO())  # type: ignore[arg-type]
    candidate = CandidateProfile(
        candidate_id="11111111-1111-4111-8111-111111111111",
        owner_subject_id="candidate-owner",
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone=None,
        location=None,
        current_title=None,
        extra_data={},
    )
    offer = Offer(
        offer_id="22222222-2222-4222-8222-222222222222",
        vacancy_id="33333333-3333-4333-8333-333333333333",
        candidate_id=candidate.candidate_id,
        status="sent",
    )
    transition = PipelineTransition(
        transition_id="66666666-6666-4666-8666-666666666666",
        vacancy_id=offer.vacancy_id,
        candidate_id=candidate.candidate_id,
        from_stage="offer",
        to_stage="hired",
        reason="accepted_offer",
        changed_by_sub="77777777-7777-4777-8777-777777777777",
        changed_by_role="hr",
        transitioned_at=datetime(2026, 3, 10, 12, 5, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="accepted offer"):
        service.build_create_payload(
            candidate=candidate,
            offer=offer,
            hired_transition=transition,
            converted_by_staff_id="77777777-7777-4777-8777-777777777777",
        )
