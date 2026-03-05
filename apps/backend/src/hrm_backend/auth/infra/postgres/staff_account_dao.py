"""PostgreSQL DAO for staff account persistence."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from hrm_backend.auth.models.staff_account import StaffAccount


class StaffAccountDAO:
    """Data-access helper for staff account rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with SQLAlchemy session."""
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
        """Create a new staff account row."""
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

    def get_by_identifier(self, identifier: str) -> StaffAccount | None:
        """Find account by login or email (case-insensitive on email)."""
        normalized = identifier.strip().lower()
        return (
            self._session.query(StaffAccount)
            .filter(or_(StaffAccount.login == normalized, StaffAccount.email == normalized))
            .first()
        )

    def get_by_login(self, login: str) -> StaffAccount | None:
        """Find account by normalized login."""
        return self._session.query(StaffAccount).filter(StaffAccount.login == login).first()

    def get_by_email(self, email: str) -> StaffAccount | None:
        """Find account by normalized email."""
        return self._session.query(StaffAccount).filter(StaffAccount.email == email).first()

    def get_by_id(self, staff_id: str) -> StaffAccount | None:
        """Find account by UUID primary key."""
        return self._session.get(StaffAccount, staff_id)
