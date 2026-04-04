"""DAO helpers for employee avatar metadata persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from hrm_backend.employee.models.avatar import EmployeeProfileAvatar


class EmployeeAvatarDAO:
    """Data-access helper for employee profile avatar metadata."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with active SQLAlchemy session.

        Args:
            session: Active request or job session.
        """
        self._session = session

    def deactivate_active_avatars(self, employee_id: str, *, commit: bool = True) -> None:
        """Mark active avatar rows as inactive for one employee profile.

        Args:
            employee_id: Employee profile identifier.
            commit: Whether to commit after the update.
        """
        self._session.query(EmployeeProfileAvatar).filter(
            EmployeeProfileAvatar.employee_id == employee_id,
            EmployeeProfileAvatar.is_active.is_(True),
        ).update(
            {
                "is_active": False,
                "updated_at": datetime.now(UTC),
            },
            synchronize_session=False,
        )
        if commit:
            self._session.commit()

    def create_avatar(
        self,
        *,
        employee_id: str,
        object_key: str,
        mime_type: str,
        size_bytes: int,
        is_active: bool,
        commit: bool = True,
    ) -> EmployeeProfileAvatar:
        """Insert new avatar metadata row.

        Args:
            employee_id: Employee profile identifier.
            object_key: Object storage key.
            mime_type: Validated MIME type.
            size_bytes: Uploaded size in bytes.
            is_active: Whether this avatar is active.
            commit: Whether to commit after insert.

        Returns:
            EmployeeProfileAvatar: Persisted avatar metadata entity.
        """
        entity = EmployeeProfileAvatar(
            employee_id=employee_id,
            object_key=object_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            is_active=is_active,
        )
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity

    def get_active_avatar(self, employee_id: str) -> EmployeeProfileAvatar | None:
        """Fetch active avatar metadata for the employee profile.

        Args:
            employee_id: Employee profile identifier.

        Returns:
            EmployeeProfileAvatar | None: Active avatar metadata or `None`.
        """
        return (
            self._session.query(EmployeeProfileAvatar)
            .filter(
                EmployeeProfileAvatar.employee_id == employee_id,
                EmployeeProfileAvatar.is_active.is_(True),
            )
            .order_by(
                EmployeeProfileAvatar.updated_at.desc(),
                EmployeeProfileAvatar.avatar_id.desc(),
            )
            .first()
        )

    def get_active_avatars_by_employee_ids(
        self, employee_ids: list[str]
    ) -> dict[str, EmployeeProfileAvatar]:
        """Batch-load active avatar rows for multiple employees.

        Args:
            employee_ids: Employee identifiers.

        Returns:
            dict[str, EmployeeProfileAvatar]: Mapping of employee_id to active avatar.
        """
        if not employee_ids:
            return {}

        rows = (
            self._session.query(EmployeeProfileAvatar)
            .filter(
                EmployeeProfileAvatar.employee_id.in_(employee_ids),
                EmployeeProfileAvatar.is_active.is_(True),
            )
            .order_by(
                EmployeeProfileAvatar.employee_id.asc(),
                EmployeeProfileAvatar.updated_at.desc(),
                EmployeeProfileAvatar.avatar_id.desc(),
            )
            .all()
        )
        avatars: dict[str, EmployeeProfileAvatar] = {}
        for row in rows:
            avatars.setdefault(row.employee_id, row)
        return avatars

    def update_avatar(
        self,
        *,
        entity: EmployeeProfileAvatar,
        commit: bool = True,
    ) -> EmployeeProfileAvatar:
        """Persist in-memory changes made to one avatar metadata row.

        Args:
            entity: Avatar metadata entity with pending changes.
            commit: Whether to commit after update.

        Returns:
            EmployeeProfileAvatar: Refreshed avatar metadata entity.
        """
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity
