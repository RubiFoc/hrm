"""Data-access helpers for employee profile persistence."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.schemas.profile import EmployeeProfileCreate


class EmployeeProfileDAO:
    """Persist and query bootstrapped employee profiles."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with an active SQLAlchemy session.

        Args:
            session: Active request or job session.
        """
        self._session = session

    def get_by_id(self, employee_id: str) -> EmployeeProfile | None:
        """Load one employee profile by identifier.

        Args:
            employee_id: Employee profile identifier.

        Returns:
            EmployeeProfile | None: Matching profile or `None`.
        """
        return self._session.get(EmployeeProfile, employee_id)

    def get_by_hire_conversion_id(self, hire_conversion_id: str) -> EmployeeProfile | None:
        """Load one employee profile by source hire-conversion identifier.

        Args:
            hire_conversion_id: Source handoff identifier.

        Returns:
            EmployeeProfile | None: Matching profile or `None`.
        """
        return (
            self._session.query(EmployeeProfile)
            .filter(EmployeeProfile.hire_conversion_id == hire_conversion_id)
            .first()
        )

    def get_by_staff_account_id(self, staff_account_id: str) -> EmployeeProfile | None:
        """Load one employee profile by linked authenticated staff-account identifier.

        Args:
            staff_account_id: Authenticated staff-account subject identifier.

        Returns:
            EmployeeProfile | None: Matching linked employee profile or `None`.
        """
        return (
            self._session.query(EmployeeProfile)
            .filter(EmployeeProfile.staff_account_id == staff_account_id)
            .first()
        )

    def list_by_email(self, email: str) -> list[EmployeeProfile]:
        """Load employee profiles matching one e-mail address case-insensitively.

        Args:
            email: Candidate or staff-account e-mail address.

        Returns:
            list[EmployeeProfile]: Matching employee profiles ordered deterministically.
        """
        normalized = email.strip().lower()
        return list(
            self._session.query(EmployeeProfile)
            .filter(func.lower(EmployeeProfile.email) == normalized)
            .order_by(
                EmployeeProfile.created_at.asc(),
                EmployeeProfile.employee_id.asc(),
            )
            .all()
        )

    def list_by_ids(self, employee_ids: list[str]) -> list[EmployeeProfile]:
        """Load employee profiles for the provided identifiers."""
        if not employee_ids:
            return []
        return list(
            self._session.query(EmployeeProfile)
            .filter(EmployeeProfile.employee_id.in_(employee_ids))
            .order_by(
                EmployeeProfile.created_at.asc(),
                EmployeeProfile.employee_id.asc(),
            )
            .all()
        )

    def list_directory(
        self,
        *,
        limit: int,
        offset: int,
        include_dismissed: bool = False,
    ) -> list[EmployeeProfile]:
        """List employee profiles for the directory view.

        Args:
            limit: Maximum number of rows.
            offset: Number of skipped rows.
            include_dismissed: Whether dismissed profiles are included.

        Returns:
            list[EmployeeProfile]: Ordered directory rows.
        """
        query = self._session.query(EmployeeProfile)
        if not include_dismissed:
            query = query.filter(EmployeeProfile.is_dismissed.is_(False))
        return list(
            query.order_by(
                EmployeeProfile.last_name.asc(),
                EmployeeProfile.first_name.asc(),
                EmployeeProfile.employee_id.asc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_directory(self, *, include_dismissed: bool = False) -> int:
        """Count employee profiles in the directory scope.

        Args:
            include_dismissed: Whether dismissed profiles are included.

        Returns:
            int: Total rows.
        """
        query = self._session.query(func.count(EmployeeProfile.employee_id))
        if not include_dismissed:
            query = query.filter(EmployeeProfile.is_dismissed.is_(False))
        total = query.scalar()
        return int(total or 0)

    def create_profile(
        self,
        *,
        payload: EmployeeProfileCreate,
        commit: bool = True,
    ) -> EmployeeProfile:
        """Insert one employee profile row.

        Args:
            payload: Typed profile payload.
            commit: When `True`, commit immediately; otherwise only flush into the current
                transaction so callers can bundle writes atomically.

        Returns:
            EmployeeProfile: Persisted employee profile entity.
        """
        entity = EmployeeProfile(
            hire_conversion_id=str(payload.hire_conversion_id),
            vacancy_id=str(payload.vacancy_id),
            candidate_id=str(payload.candidate_id),
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            phone=payload.phone,
            location=payload.location,
            current_title=payload.current_title,
            extra_data_json=payload.extra_data,
            offer_terms_summary=payload.offer_terms_summary,
            start_date=payload.start_date,
            created_by_staff_id=str(payload.created_by_staff_id),
        )
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity

    def update_profile(
        self,
        *,
        entity: EmployeeProfile,
        commit: bool = True,
    ) -> EmployeeProfile:
        """Persist in-memory changes made to one employee profile entity.

        Args:
            entity: Employee profile entity with pending mutations.
            commit: When `True`, commit immediately; otherwise only flush into the current
                transaction.

        Returns:
            EmployeeProfile: Refreshed persisted employee profile entity.
        """
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity
