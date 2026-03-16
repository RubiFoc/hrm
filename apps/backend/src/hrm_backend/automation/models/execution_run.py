"""Persistence model for durable automation execution runs.

This table captures one executor invocation for a single trigger event. It is designed
to support operational traceability without storing additional PII.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class AutomationExecutionRun(Base):
    """One durable automation execution run for a trigger event.

    Attributes:
        run_id: Unique run identifier.
        event_type: Trigger key (for example `pipeline.transition_appended`).
        trigger_event_id: Stable domain identifier used as the event fingerprint.
        event_time: Trigger event timestamp (UTC).
        correlation_id: Request correlation id (`X-Request-ID`) when available.
        trace_id: Generated trace id used to correlate logs and failures.
        status: Run status (`running`, `succeeded`, `failed`).
        planned_action_count: Number of planned actions for the run.
        succeeded_action_count: Number of actions that executed successfully.
        deduped_action_count: Number of actions that were skipped due to dedupe.
        failed_action_count: Number of actions that failed.
        error_kind: Sanitized failure kind for run-level failures.
        error_text: Sanitized + truncated failure text for run-level failures.
        started_at: Run start timestamp (UTC).
        finished_at: Run finish timestamp (UTC) when terminal.
        updated_at: Update timestamp (UTC).
    """

    __tablename__ = "automation_execution_runs"
    __table_args__ = (
        Index(
            "ix_automation_execution_runs_event_trigger_time",
            "event_type",
            "trigger_event_id",
            "event_time",
        ),
        Index(
            "ix_automation_execution_runs_status_started_at",
            "status",
            "started_at",
        ),
        Index(
            "ix_automation_execution_runs_correlation_id",
            "correlation_id",
        ),
        Index(
            "ix_automation_execution_runs_trace_id",
            "trace_id",
        ),
    )

    run_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    trigger_event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    planned_action_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    succeeded_action_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deduped_action_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_action_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_kind: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_text: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

