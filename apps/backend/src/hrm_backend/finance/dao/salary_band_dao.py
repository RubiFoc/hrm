"""DAO helpers for vacancy salary-band history."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from hrm_backend.finance.models.salary_band import SalaryBand


class SalaryBandDAO:
    """Data-access helper for salary-band history rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with active SQLAlchemy session."""
        self._session = session

    def create(
        self,
        *,
        entity: SalaryBand,
        commit: bool = True,
    ) -> SalaryBand:
        """Persist a new salary band entry."""
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity
        self._session.flush()
        return entity

    def list_by_vacancy_id(self, vacancy_id: str) -> list[SalaryBand]:
        """List salary-band history for one vacancy ordered by version."""
        return list(
            self._session.query(SalaryBand)
            .filter(SalaryBand.vacancy_id == vacancy_id)
            .order_by(SalaryBand.band_version.desc(), SalaryBand.band_id.asc())
            .all()
        )

    def list_by_vacancy_ids(self, vacancy_ids: list[str]) -> list[SalaryBand]:
        """List salary bands for multiple vacancies."""
        if not vacancy_ids:
            return []
        return list(
            self._session.query(SalaryBand)
            .filter(SalaryBand.vacancy_id.in_(vacancy_ids))
            .order_by(SalaryBand.band_version.desc(), SalaryBand.band_id.asc())
            .all()
        )

    def get_latest_version(self, vacancy_id: str) -> int:
        """Return the latest band version for one vacancy."""
        latest = (
            self._session.query(func.max(SalaryBand.band_version))
            .filter(SalaryBand.vacancy_id == vacancy_id)
            .scalar()
        )
        return int(latest or 0)
