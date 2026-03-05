"""PostgreSQL DAO for admin-issued employee registration keys."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, or_
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

    def get_by_id(self, key_id: str) -> EmployeeRegistrationKey | None:
        """Find key row by internal UUID identifier.

        Args:
            key_id: Key identifier from API path.

        Returns:
            EmployeeRegistrationKey | None: Matched key row if it exists.
        """
        return self._session.get(EmployeeRegistrationKey, key_id)

    def list_keys(
        self,
        *,
        limit: int,
        offset: int,
        target_role: str | None = None,
        status: str | None = None,
        created_by_staff_id: str | None = None,
        search: str | None = None,
    ) -> list[EmployeeRegistrationKey]:
        """List registration keys with server-driven pagination and filters.

        Args:
            limit: Maximum number of rows to return.
            offset: Number of rows to skip from ordered result.
            target_role: Optional exact target role filter.
            status: Optional lifecycle status filter.
            created_by_staff_id: Optional exact issuer staff identifier.
            search: Optional case-insensitive search term for key identifiers.

        Returns:
            list[EmployeeRegistrationKey]: Ordered and filtered key rows.
        """
        query = self._build_list_query(
            target_role=target_role,
            status=status,
            created_by_staff_id=created_by_staff_id,
            search=search,
        )
        return list(
            query.order_by(
                EmployeeRegistrationKey.created_at.desc(),
                EmployeeRegistrationKey.key_id.desc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_keys(
        self,
        *,
        target_role: str | None = None,
        status: str | None = None,
        created_by_staff_id: str | None = None,
        search: str | None = None,
    ) -> int:
        """Count keys matching optional list filters.

        Args:
            target_role: Optional exact target role filter.
            status: Optional lifecycle status filter.
            created_by_staff_id: Optional exact issuer staff identifier.
            search: Optional case-insensitive search term for key identifiers.

        Returns:
            int: Total number of matching rows.
        """
        query = self._build_list_query(
            target_role=target_role,
            status=status,
            created_by_staff_id=created_by_staff_id,
            search=search,
        )
        total = query.with_entities(func.count(EmployeeRegistrationKey.key_id)).scalar()
        return int(total or 0)

    def revoke_key(
        self,
        *,
        entity: EmployeeRegistrationKey,
        revoked_at: datetime,
        revoked_by_staff_id: str,
    ) -> EmployeeRegistrationKey:
        """Mark existing key as revoked.

        Args:
            entity: Existing key entity to mutate.
            revoked_at: Revocation timestamp.
            revoked_by_staff_id: Staff identifier that revoked the key.

        Returns:
            EmployeeRegistrationKey: Persisted and refreshed key entity.
        """
        entity.revoked_at = revoked_at
        entity.revoked_by_staff_id = revoked_by_staff_id
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def _build_list_query(
        self,
        *,
        target_role: str | None,
        status: str | None,
        created_by_staff_id: str | None,
        search: str | None,
    ):
        """Build base filtered query for list/count operations.

        Args:
            target_role: Optional exact target role filter.
            status: Optional lifecycle status filter.
            created_by_staff_id: Optional exact issuer staff identifier.
            search: Optional case-insensitive search term for key identifiers.

        Returns:
            sqlalchemy.orm.Query[EmployeeRegistrationKey]: Filtered query object.
        """
        now = datetime.now(UTC)
        query = self._session.query(EmployeeRegistrationKey)

        if target_role is not None and target_role.strip():
            query = query.filter(EmployeeRegistrationKey.target_role == target_role.strip().lower())

        if created_by_staff_id is not None and created_by_staff_id.strip():
            query = query.filter(
                EmployeeRegistrationKey.created_by_staff_id == created_by_staff_id.strip().lower()
            )

        if search is not None and search.strip():
            normalized_search = search.strip().lower()
            query = query.filter(
                or_(
                    func.lower(EmployeeRegistrationKey.key_id).contains(normalized_search),
                    func.lower(EmployeeRegistrationKey.employee_key).contains(normalized_search),
                )
            )

        if status is not None:
            normalized_status = status.strip().lower()
            if normalized_status == "active":
                query = query.filter(
                    EmployeeRegistrationKey.revoked_at.is_(None),
                    EmployeeRegistrationKey.used_at.is_(None),
                    EmployeeRegistrationKey.expires_at > now,
                )
            elif normalized_status == "used":
                query = query.filter(
                    EmployeeRegistrationKey.revoked_at.is_(None),
                    EmployeeRegistrationKey.used_at.is_not(None),
                )
            elif normalized_status == "expired":
                query = query.filter(
                    EmployeeRegistrationKey.revoked_at.is_(None),
                    EmployeeRegistrationKey.used_at.is_(None),
                    EmployeeRegistrationKey.expires_at <= now,
                )
            elif normalized_status == "revoked":
                query = query.filter(EmployeeRegistrationKey.revoked_at.is_not(None))

        return query
