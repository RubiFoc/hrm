"""Persistence model for durable recruitment-to-employee handoff rows."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base
from hrm_backend.employee.utils.conversions import HIRE_CONVERSION_STATUS_READY


class HireConversion(Base):
    """Frozen handoff artifact created when an accepted offer becomes `hired`.

    Attributes:
        conversion_id: Unique conversion identifier.
        vacancy_id: Source vacancy identifier.
        candidate_id: Source candidate identifier.
        offer_id: Accepted offer identifier used for the conversion.
        hired_transition_id: Pipeline transition identifier for `offer -> hired`.
        status: Minimal handoff lifecycle state.
        candidate_snapshot_json: Frozen candidate bootstrap payload for employee-profile creation.
        offer_snapshot_json: Frozen accepted-offer payload for employee bootstrap.
        converted_at: Timestamp when the durable handoff was created.
        converted_by_staff_id: Staff subject that performed the `hired` transition.
    """

    __tablename__ = "hire_conversions"
    __table_args__ = (
        Index(
            "ux_hire_conversions_vacancy_candidate",
            "vacancy_id",
            "candidate_id",
            unique=True,
        ),
        Index(
            "ux_hire_conversions_hired_transition",
            "hired_transition_id",
            unique=True,
        ),
        Index("ix_hire_conversions_status", "status"),
    )

    conversion_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    vacancy_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("vacancies.vacancy_id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_profiles.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    offer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("offers.offer_id", ondelete="CASCADE"),
        nullable=False,
    )
    hired_transition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("pipeline_transitions.transition_id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=HIRE_CONVERSION_STATUS_READY,
    )
    candidate_snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    offer_snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    converted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    converted_by_staff_id: Mapped[str] = mapped_column(String(36), nullable=False)
