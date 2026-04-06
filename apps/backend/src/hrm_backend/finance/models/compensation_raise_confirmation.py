"""Persistence model for raise request confirmations."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class CompensationRaiseConfirmation(Base):
    """Manager confirmation record for a raise request.

    Attributes:
        confirmation_id: Unique confirmation identifier.
        raise_request_id: Linked raise request identifier.
        manager_staff_id: Manager staff identifier who confirmed the request.
        confirmed_at: Timestamp when confirmation was recorded.
    """

    __tablename__ = "compensation_raise_confirmations"
    __table_args__ = (
        Index(
            "ux_comp_raise_confirmations_request_manager",
            "raise_request_id",
            "manager_staff_id",
            unique=True,
        ),
        Index("ix_comp_raise_confirmations_request_id", "raise_request_id"),
    )

    confirmation_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    raise_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("compensation_raise_requests.request_id", ondelete="CASCADE"),
        nullable=False,
    )
    manager_staff_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("staff_accounts.staff_id", ondelete="RESTRICT"),
        nullable=False,
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
