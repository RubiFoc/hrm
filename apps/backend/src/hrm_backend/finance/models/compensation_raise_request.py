"""Persistence model for compensation raise requests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class CompensationRaiseRequest(Base):
    """Manager-initiated raise request with leader decision metadata.

    Attributes:
        request_id: Unique raise request identifier.
        employee_id: Target employee profile identifier.
        requested_by_staff_id: Manager staff identifier who created the request.
        requested_at: Timestamp when the request was submitted.
        effective_date: Date when the raise should take effect.
        proposed_base_salary: Requested base salary after the raise.
        currency: Currency code (fixed to BYN by policy).
        status: Current request status.
        leader_decision_by_staff_id: Leader staff identifier for final decision.
        leader_decision_at: Timestamp when leader decision was recorded.
        leader_decision_note: Optional leader decision note.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "compensation_raise_requests"
    __table_args__ = (
        Index("ix_comp_raise_requests_employee_id", "employee_id"),
        Index("ix_comp_raise_requests_status", "status"),
        Index("ix_comp_raise_requests_requested_at", "requested_at"),
    )

    request_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("employee_profiles.employee_id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by_staff_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("staff_accounts.staff_id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    proposed_base_salary: Mapped[float] = mapped_column(
        Numeric(12, 2, asdecimal=False),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BYN")
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    leader_decision_by_staff_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("staff_accounts.staff_id", ondelete="RESTRICT"),
        nullable=True,
    )
    leader_decision_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    leader_decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
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
