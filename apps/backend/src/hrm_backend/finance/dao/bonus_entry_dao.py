"""DAO helpers for manual bonus entries."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from hrm_backend.finance.models.bonus_entry import BonusEntry


class BonusEntryDAO:
    """Data-access helper for bonus entry persistence."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with active SQLAlchemy session."""
        self._session = session

    def get_by_employee_and_month(self, employee_id: str, period_month: date) -> BonusEntry | None:
        """Fetch a bonus entry by employee identifier and month."""
        return (
            self._session.query(BonusEntry)
            .filter(
                BonusEntry.employee_id == employee_id,
                BonusEntry.period_month == period_month,
            )
            .first()
        )

    def list_by_employee_ids(self, employee_ids: list[str]) -> list[BonusEntry]:
        """List bonus entries for the provided employee identifiers."""
        if not employee_ids:
            return []
        return list(
            self._session.query(BonusEntry)
            .filter(BonusEntry.employee_id.in_(employee_ids))
            .order_by(BonusEntry.period_month.desc(), BonusEntry.bonus_id.asc())
            .all()
        )

    def create(
        self,
        *,
        entity: BonusEntry,
        commit: bool = True,
    ) -> BonusEntry:
        """Persist a new bonus entry."""
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity
        self._session.flush()
        return entity

    def update(
        self,
        *,
        entity: BonusEntry,
        commit: bool = True,
    ) -> BonusEntry:
        """Persist in-memory updates to a bonus entry."""
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity
        self._session.flush()
        return entity
