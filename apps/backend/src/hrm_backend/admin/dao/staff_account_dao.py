"""PostgreSQL DAO for admin-managed staff account operations."""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from hrm_backend.auth.models.staff_account import StaffAccount


class AdminStaffAccountDAO:
    """Data-access helper for admin staff account flows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def create_account(
        self,
        *,
        login: str,
        email: str,
        password_hash: str,
        role: str,
        is_active: bool = True,
    ) -> StaffAccount:
        """Create a new staff account row.

        Args:
            login: Normalized login value.
            email: Normalized email value.
            password_hash: Password hash string.
            role: Staff role claim.
            is_active: Active-state flag.

        Returns:
            StaffAccount: Persisted staff account row.
        """
        entity = StaffAccount(
            login=login,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def get_by_id(self, staff_id: str) -> StaffAccount | None:
        """Find account by UUID primary key."""
        return self._session.get(StaffAccount, staff_id)

    def get_by_login(self, login: str) -> StaffAccount | None:
        """Find account by normalized login."""
        return self._session.query(StaffAccount).filter(StaffAccount.login == login).first()

    def get_by_email(self, email: str) -> StaffAccount | None:
        """Find account by normalized email."""
        return self._session.query(StaffAccount).filter(StaffAccount.email == email).first()

    def list_accounts(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> list[StaffAccount]:
        """List staff accounts with server-driven pagination and filters.

        Args:
            limit: Maximum number of rows to return.
            offset: Number of rows to skip from ordered result.
            search: Optional case-insensitive search term for login/e-mail.
            role: Optional exact role filter.
            is_active: Optional exact active-state filter.

        Returns:
            list[StaffAccount]: Ordered and filtered staff account rows.
        """
        query = self._build_list_query(search=search, role=role, is_active=is_active)
        return list(
            query.order_by(StaffAccount.created_at.desc(), StaffAccount.staff_id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_accounts(
        self,
        *,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        """Count staff accounts matching optional list filters.

        Args:
            search: Optional case-insensitive search term for login/e-mail.
            role: Optional exact role filter.
            is_active: Optional exact active-state filter.

        Returns:
            int: Total number of matching rows.
        """
        query = self._build_list_query(search=search, role=role, is_active=is_active)
        total = query.with_entities(func.count(StaffAccount.staff_id)).scalar()
        return int(total or 0)

    def update_account_fields(
        self,
        *,
        entity: StaffAccount,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> StaffAccount:
        """Update mutable staff account fields and persist row.

        Args:
            entity: Existing staff account entity to update.
            role: Optional replacement role value.
            is_active: Optional replacement active-state value.

        Returns:
            StaffAccount: Persisted and refreshed account entity.
        """
        if role is not None:
            entity.role = role
        if is_active is not None:
            entity.is_active = is_active

        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def count_active_admins(self) -> int:
        """Count currently active accounts with `admin` role.

        Returns:
            int: Number of active admin accounts.
        """
        total = (
            self._session.query(func.count(StaffAccount.staff_id))
            .filter(
                StaffAccount.role == "admin",
                StaffAccount.is_active.is_(True),
            )
            .scalar()
        )
        return int(total or 0)

    def _build_list_query(
        self,
        *,
        search: str | None,
        role: str | None,
        is_active: bool | None,
    ):
        """Build base filtered query for list/count operations.

        Args:
            search: Optional case-insensitive search term for login/e-mail.
            role: Optional exact role filter.
            is_active: Optional exact active-state filter.

        Returns:
            sqlalchemy.orm.Query[StaffAccount]: Filtered query object.
        """
        query = self._session.query(StaffAccount)

        if search is not None and search.strip():
            normalized_search = search.strip().lower()
            query = query.filter(
                or_(
                    func.lower(StaffAccount.login).contains(normalized_search),
                    func.lower(StaffAccount.email).contains(normalized_search),
                )
            )

        if role is not None and role.strip():
            query = query.filter(StaffAccount.role == role.strip().lower())

        if is_active is not None:
            query = query.filter(StaffAccount.is_active.is_(is_active))

        return query
