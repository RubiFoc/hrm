"""Persistence model for durable automation KPI metric events."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class AutomationMetricEvent(Base):
    """One durable automation KPI event row.

    Attributes:
        metric_event_id: Unique metric event identifier.
        event_type: Trigger key (for example `pipeline.transition_appended`).
        trigger_event_id: Stable domain identifier used as the event fingerprint.
        event_time: Trigger event timestamp (UTC).
        outcome: Derived automation outcome (`no_rules`, `success`, `deduped`, `failed`).
        total_hr_operations_count: Count contribution to the monthly denominator.
        automated_hr_operations_count: Count contribution to the monthly numerator.
        planned_action_count: Number of planned actions for the trigger event.
        succeeded_action_count: Number of action attempts that succeeded.
        deduped_action_count: Number of action attempts that were skipped as duplicates.
        failed_action_count: Number of action attempts that failed.
        created_at: Creation timestamp (UTC).
        updated_at: Update timestamp (UTC).
    """

    __tablename__ = "automation_metric_events"
    __table_args__ = (
        Index(
            "ux_automation_metric_events_event_trigger",
            "event_type",
            "trigger_event_id",
            unique=True,
        ),
        Index("ix_automation_metric_events_event_time", "event_time"),
        Index("ix_automation_metric_events_outcome", "outcome"),
    )

    metric_event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    trigger_event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    total_hr_operations_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    automated_hr_operations_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planned_action_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    succeeded_action_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deduped_action_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_action_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
