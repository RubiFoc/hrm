"""Business service for durable hire-conversion handoff creation."""

from __future__ import annotations

from uuid import UUID

from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.employee.dao.hire_conversion_dao import HireConversionDAO
from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.schemas.conversion import (
    HireConversionCandidateSnapshot,
    HireConversionCreate,
    HireConversionOfferSnapshot,
)
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition


class HireConversionService:
    """Build and persist durable employee-domain handoff artifacts after hiring."""

    def __init__(self, *, dao: HireConversionDAO) -> None:
        """Initialize service with DAO dependency.

        Args:
            dao: Hire-conversion DAO.
        """
        self._dao = dao

    def build_create_payload(
        self,
        *,
        candidate: CandidateProfile,
        offer: Offer,
        hired_transition: PipelineTransition,
        converted_by_staff_id: str,
    ) -> HireConversionCreate:
        """Build a deterministic handoff payload from accepted-offer source entities.

        Args:
            candidate: Candidate profile linked to the hire.
            offer: Accepted offer used for the conversion.
            hired_transition: Persisted `offer -> hired` pipeline transition.
            converted_by_staff_id: Staff subject that executed the transition.

        Returns:
            HireConversionCreate: Fully-typed payload ready for persistence.

        Raises:
            ValueError: If the source offer is not accepted or the transition is not `hired`.
        """
        if offer.status != "accepted":
            raise ValueError("Hire conversion requires an accepted offer")
        if hired_transition.to_stage != "hired":
            raise ValueError("Hire conversion requires a `hired` pipeline transition")

        return HireConversionCreate(
            vacancy_id=UUID(offer.vacancy_id),
            candidate_id=UUID(candidate.candidate_id),
            offer_id=UUID(offer.offer_id),
            hired_transition_id=UUID(hired_transition.transition_id),
            candidate_snapshot=HireConversionCandidateSnapshot(
                first_name=candidate.first_name,
                last_name=candidate.last_name,
                email=candidate.email,
                phone=candidate.phone,
                location=candidate.location,
                current_title=candidate.current_title,
                extra_data=dict(candidate.extra_data or {}),
            ),
            offer_snapshot=HireConversionOfferSnapshot(
                status="accepted",
                terms_summary=offer.terms_summary,
                proposed_start_date=offer.proposed_start_date,
                expires_at=offer.expires_at,
                note=offer.note,
                sent_at=offer.sent_at,
                sent_by_staff_id=(
                    UUID(offer.sent_by_staff_id) if offer.sent_by_staff_id is not None else None
                ),
                decision_at=offer.decision_at,
                decision_note=offer.decision_note,
                decision_recorded_by_staff_id=(
                    UUID(offer.decision_recorded_by_staff_id)
                    if offer.decision_recorded_by_staff_id is not None
                    else None
                ),
            ),
            converted_by_staff_id=UUID(converted_by_staff_id),
        )

    def create_ready_handoff(
        self,
        *,
        candidate: CandidateProfile,
        offer: Offer,
        hired_transition: PipelineTransition,
        converted_by_staff_id: str,
        commit: bool = True,
    ) -> HireConversion:
        """Persist one ready-state handoff artifact for downstream employee bootstrap.

        Args:
            candidate: Candidate profile linked to the hire.
            offer: Accepted offer used for the conversion.
            hired_transition: Pipeline transition for `offer -> hired`.
            converted_by_staff_id: Staff subject that executed the transition.
            commit: When `True`, commit immediately; otherwise participate in the caller's
                transaction bundle.

        Returns:
            HireConversion: Persisted handoff entity.
        """
        payload = self.build_create_payload(
            candidate=candidate,
            offer=offer,
            hired_transition=hired_transition,
            converted_by_staff_id=converted_by_staff_id,
        )
        return self._dao.create_conversion(payload=payload, commit=commit)
