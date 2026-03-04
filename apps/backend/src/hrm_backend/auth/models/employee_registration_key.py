"""Persistence model for one-time employee registration keys."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class EmployeeRegistrationKey(Base):
    """One-time UUID key used for staff self-registration.

    Attributes:
        key_id: Internal key row identifier.
        employee_key: External one-time key value.
        target_role: Role that can be registered with this key.
        expires_at: Key expiration timestamp.
        used_at: Consumption timestamp.
        created_by_staff_id: Staff id that issued key.
        created_at: Issued timestamp.
    """

    __tablename__ = "employee_registration_keys"
    __table_args__ = (
        Index("ix_employee_registration_keys_employee_key", "employee_key", unique=True),
        Index("ix_employee_registration_keys_expires_at", "expires_at"),
    )

    key_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    employee_key: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    target_role: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_staff_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("staff_accounts.staff_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
