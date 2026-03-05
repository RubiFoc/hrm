"""PostgreSQL DAO for admin-issued employee registration keys."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from hrm_backend.auth.models.employee_registration_key import EmployeeRegistrationKey


class AdminEmployeeRegistrationKeyDAO:
    """Data-access helper for admin employee-registration-key flows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def create_key(
        self,
        *,
        target_role: str,
        created_by_staff_id: str,
        ttl_seconds: int,
    ) -> EmployeeRegistrationKey:
        """Create one-time registration key with TTL.

        Args:
            target_role: Role claim that can consume the key.
            created_by_staff_id: Admin staff identifier that issued the key.
            ttl_seconds: Validity window in seconds.

        Returns:
            EmployeeRegistrationKey: Persisted key row.
        """
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
