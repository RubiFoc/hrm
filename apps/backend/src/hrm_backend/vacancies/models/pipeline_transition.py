"""Pipeline transition history persistence model."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class PipelineTransition(Base):
    """Append-only candidate pipeline transition event.

    Attributes:
        transition_id: Unique transition identifier.
        vacancy_id: Linked vacancy identifier.
        candidate_id: Linked candidate identifier.
        from_stage: Previous pipeline stage.
        to_stage: New pipeline stage.
        reason: Optional transition reason.
        changed_by_sub: Actor subject identifier.
        changed_by_role: Actor role claim.
        transitioned_at: Transition timestamp.
    """

    __tablename__ = "pipeline_transitions"
    __table_args__ = (
        Index(
            "ix_pipeline_transitions_vacancy_candidate_time",
            "vacancy_id",
            "candidate_id",
            "transitioned_at",
        ),
    )

    transition_id: Mapped[str] = mapped_column(
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
    from_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by_sub: Mapped[str] = mapped_column(String(128), nullable=False)
    changed_by_role: Mapped[str] = mapped_column(String(64), nullable=False)
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
