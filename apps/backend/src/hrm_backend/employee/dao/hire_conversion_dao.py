"""Data-access helpers for persisted hire-conversion handoff rows."""

from __future__ import annotations

from sqlalchemy.orm import Session

from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.schemas.conversion import HireConversionCreate


class HireConversionDAO:
    """Persist and query durable recruitment-to-employee handoff rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with active SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def get_by_pair(self, *, vacancy_id: str, candidate_id: str) -> HireConversion | None:
        """Load one conversion row by vacancy-candidate pair.

        Args:
            vacancy_id: Vacancy identifier.
            candidate_id: Candidate identifier.

        Returns:
            HireConversion | None: Matching row or `None`.
        """
        return (
            self._session.query(HireConversion)
            .filter(
                HireConversion.vacancy_id == vacancy_id,
                HireConversion.candidate_id == candidate_id,
            )
            .first()
        )

    def create_conversion(
        self,
        *,
        payload: HireConversionCreate,
        commit: bool = True,
    ) -> HireConversion:
        """Insert one durable hire-conversion handoff row.

        Args:
            payload: Typed conversion payload.
            commit: When `True`, commit immediately; otherwise only flush into the current
                transaction so callers can bundle writes atomically.

        Returns:
            HireConversion: Persisted conversion entity.
        """
        entity = HireConversion(
            vacancy_id=str(payload.vacancy_id),
            candidate_id=str(payload.candidate_id),
            offer_id=str(payload.offer_id),
            hired_transition_id=str(payload.hired_transition_id),
            status=payload.status,
            candidate_snapshot_json=payload.candidate_snapshot.model_dump(mode="json"),
            offer_snapshot_json=payload.offer_snapshot.model_dump(mode="json"),
            converted_by_staff_id=str(payload.converted_by_staff_id),
        )
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity
