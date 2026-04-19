"""PostgreSQL DAO for department reference data."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from hrm_backend.departments.models.department import Department


class DepartmentDAO:
    """Data-access helper for department reference rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def create_department(self, *, name: str) -> Department:
        """Create a new department row.

        Args:
            name: Normalized department name.

        Returns:
            Department: Persisted department entity.
        """
        entity = Department(name=name)
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def get_by_id(self, department_id: str) -> Department | None:
        """Fetch department by identifier."""
        return self._session.get(Department, department_id)

    def get_by_name(self, name: str) -> Department | None:
        """Fetch department by exact name (case-insensitive)."""
        normalized = name.strip().lower()
        if not normalized:
            return None
        return (
            self._session.query(Department)
            .filter(func.lower(Department.name) == normalized)
            .first()
        )

    def list_departments(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
    ) -> list[Department]:
        """List departments with pagination and optional search.

        Args:
            limit: Maximum number of rows to return.
            offset: Offset for pagination.
            search: Optional search term for case-insensitive name match.

        Returns:
            list[Department]: Ordered department rows.
        """
        query = self._build_list_query(search=search)
        return list(
            query.order_by(Department.name.asc(), Department.department_id.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_departments(self, *, search: str | None = None) -> int:
        """Count departments for pagination.

        Args:
            search: Optional search term for case-insensitive name match.

        Returns:
            int: Total number of matching rows.
        """
        query = self._build_list_query(search=search)
        total = query.with_entities(func.count(Department.department_id)).scalar()
        return int(total or 0)

    def update_department(self, *, entity: Department, name: str) -> Department:
        """Update mutable department fields and persist row.

        Args:
            entity: Department entity to update.
            name: Normalized department name.

        Returns:
            Department: Persisted department entity.
        """
        entity.name = name
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def _build_list_query(self, *, search: str | None):
        """Build base query for list and count operations.

        Args:
            search: Optional search term for case-insensitive name match.

        Returns:
            sqlalchemy.orm.Query[Department]: Filtered query object.
        """
        query = self._session.query(Department)
        if search is not None and search.strip():
            normalized_search = search.strip().lower()
            query = query.filter(func.lower(Department.name).contains(normalized_search))
        return query
