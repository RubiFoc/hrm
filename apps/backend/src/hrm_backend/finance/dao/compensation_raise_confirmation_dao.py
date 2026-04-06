"""DAO helpers for raise request confirmations."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from hrm_backend.finance.models.compensation_raise_confirmation import (
    CompensationRaiseConfirmation,
)


class CompensationRaiseConfirmationDAO:
    """Data-access helper for raise request confirmations."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with active SQLAlchemy session."""
        self._session = session

    def create(
        self,
        *,
        entity: CompensationRaiseConfirmation,
        commit: bool = True,
    ) -> CompensationRaiseConfirmation:
        """Persist a new confirmation entry."""
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity
        self._session.flush()
        return entity

    def list_by_request_id(self, request_id: str) -> list[CompensationRaiseConfirmation]:
        """List confirmations for one raise request."""
        return list(
            self._session.query(CompensationRaiseConfirmation)
            .filter(CompensationRaiseConfirmation.raise_request_id == request_id)
            .order_by(
                CompensationRaiseConfirmation.confirmed_at.asc(),
                CompensationRaiseConfirmation.confirmation_id.asc(),
            )
            .all()
        )

    def list_by_request_ids(self, request_ids: list[str]) -> list[CompensationRaiseConfirmation]:
        """List confirmations for the provided raise request identifiers."""
        if not request_ids:
            return []
        return list(
            self._session.query(CompensationRaiseConfirmation)
            .filter(CompensationRaiseConfirmation.raise_request_id.in_(request_ids))
            .order_by(
                CompensationRaiseConfirmation.confirmed_at.asc(),
                CompensationRaiseConfirmation.confirmation_id.asc(),
            )
            .all()
        )

    def count_by_request_id(self, request_id: str) -> int:
        """Count confirmations for one raise request."""
        total = (
            self._session.query(func.count(CompensationRaiseConfirmation.confirmation_id))
            .filter(CompensationRaiseConfirmation.raise_request_id == request_id)
            .scalar()
        )
        return int(total or 0)
