"""Persistence model for manual bonus entries."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class BonusEntry(Base):
    """Manual bonus entry for one employee and month.

    Attributes:
        bonus_id: Unique bonus entry identifier.
        employee_id: Employee profile identifier.
        period_month: First day of bonus month.
        amount: Bonus amount for the month.
        currency: Currency code (fixed to BYN by policy).
        note: Optional bonus note.
        created_by_staff_id: Staff identifier who created the entry.
        updated_by_staff_id: Staff identifier who last updated the entry.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "compensation_bonus_entries"
    __table_args__ = (
        Index("ux_comp_bonus_entries_employee_month", "employee_id", "period_month", unique=True),
        Index("ix_comp_bonus_entries_employee_id", "employee_id"),
        Index("ix_comp_bonus_entries_period_month", "period_month"),
    )

    bonus_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("employee_profiles.employee_id", ondelete="CASCADE"),
        nullable=False,
    )
    period_month: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2, asdecimal=False), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BYN")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_staff_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("staff_accounts.staff_id", ondelete="RESTRICT"),
        nullable=False,
    )
    updated_by_staff_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("staff_accounts.staff_id", ondelete="RESTRICT"),
        nullable=True,
    )
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
