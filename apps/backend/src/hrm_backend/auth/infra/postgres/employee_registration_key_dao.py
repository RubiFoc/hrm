"""PostgreSQL DAO for one-time employee registration keys."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from hrm_backend.auth.models.employee_registration_key import EmployeeRegistrationKey


class EmployeeRegistrationKeyDAO:
    """Data-access helper for employee registration key rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with SQLAlchemy session."""
        self._session = session

    def create_key(
        self,
        *,
        target_role: str,
        created_by_staff_id: str,
        ttl_seconds: int,
    ) -> EmployeeRegistrationKey:
        """Create one-time registration key with TTL."""
        entity = EmployeeRegistrationKey(
            employee_key=str(uuid4()),
            target_role=target_role,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
            created_by_staff_id=created_by_staff_id,
        )
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def get_by_employee_key(self, employee_key: str) -> EmployeeRegistrationKey | None:
        """Find key row by external UUID value."""
        return (
            self._session.query(EmployeeRegistrationKey)
            .filter(EmployeeRegistrationKey.employee_key == employee_key)
            .first()
        )

    def consume_key(
        self,
        *,
        employee_key: str,
        target_role: str,
    ) -> EmployeeRegistrationKey | None:
        """Atomically consume key if it is valid, active, and role-matched."""
        now = datetime.now(UTC)
        entity = (
            self._session.query(EmployeeRegistrationKey)
            .filter(
                EmployeeRegistrationKey.employee_key == employee_key,
                EmployeeRegistrationKey.target_role == target_role,
                EmployeeRegistrationKey.used_at.is_(None),
                EmployeeRegistrationKey.expires_at > now,
            )
            .first()
        )
        if entity is None:
            return None

        entity.used_at = now
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity
