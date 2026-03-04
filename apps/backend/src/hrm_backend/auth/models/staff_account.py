"""Persistence model for staff authentication accounts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class StaffAccount(Base):
    """Staff account used for password-based authentication.

    Attributes:
        staff_id: Unique staff identifier.
        login: Unique login/username.
        email: Unique normalized email.
        password_hash: Argon2id hash string.
        role: Staff role claim.
        is_active: Whether account can authenticate.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "staff_accounts"
    __table_args__ = (
        Index("ix_staff_accounts_login", "login", unique=True),
        Index("ix_staff_accounts_email", "email", unique=True),
    )

    staff_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    login: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
