"""Data-access helpers for persisted offer lifecycle rows."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from hrm_backend.vacancies.models.offer import Offer


class OfferDAO:
    """Persist and query offer rows scoped to vacancy-candidate pairs."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with active SQLAlchemy session."""
        self._session = session

    def get_by_pair(self, *, vacancy_id: str, candidate_id: str) -> Offer | None:
        """Load one offer row by vacancy-candidate pair."""
        return (
            self._session.query(Offer)
            .filter(
                Offer.vacancy_id == vacancy_id,
                Offer.candidate_id == candidate_id,
            )
            .first()
        )

    def create_offer(
        self,
        *,
        vacancy_id: str,
        candidate_id: str,
        terms_summary: str | None = None,
        proposed_start_date: date | None = None,
        expires_at: date | None = None,
        note: str | None = None,
    ) -> Offer:
        """Insert one draft offer row for the selected vacancy-candidate pair."""
        entity = Offer(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            status="draft",
            terms_summary=terms_summary,
            proposed_start_date=proposed_start_date,
            expires_at=expires_at,
            note=note,
        )
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def update_offer_draft(
        self,
        *,
        entity: Offer,
        terms_summary: str,
        proposed_start_date: date | None,
        expires_at: date | None,
        note: str | None,
    ) -> Offer:
        """Replace mutable draft fields and persist changes."""
        entity.terms_summary = terms_summary
        entity.proposed_start_date = proposed_start_date
        entity.expires_at = expires_at
        entity.note = note
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def mark_sent(self, *, entity: Offer, sent_by_staff_id: str) -> Offer:
        """Move draft offer to sent state and persist sender metadata."""
        entity.status = "sent"
        entity.sent_at = datetime.now(UTC)
        entity.sent_by_staff_id = sent_by_staff_id
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def mark_decision(
        self,
        *,
        entity: Offer,
        status: str,
        decision_note: str | None,
        decision_recorded_by_staff_id: str,
    ) -> Offer:
        """Persist accepted/declined state for one sent offer."""
        entity.status = status
        entity.decision_at = datetime.now(UTC)
        entity.decision_note = decision_note
        entity.decision_recorded_by_staff_id = decision_recorded_by_staff_id
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity
