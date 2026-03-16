"""Persistence model for durable automation action execution attempts.

This table stores one action attempt linked to an execution run. The stored fields are
restricted to non-PII technical identifiers and sanitized error metadata.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class AutomationActionExecution(Base):
    """One durable automation action execution attempt.

    Attributes:
        action_execution_id: Unique action execution identifier.
        run_id: Owning execution run identifier.
        action: Action key (v1: `notification.emit`).
        rule_id: Automation rule identifier that produced the action.
        recipient_staff_id: Recipient staff identifier for recipient-scoped actions.
        recipient_role: Recipient role snapshot.
        source_type: Domain source type for traceability.
        source_id: Domain source identifier for traceability.
        dedupe_key: Executor idempotency key used to dedupe side effects.
        status: Action status (`succeeded`, `deduped`, `failed`).
        attempt_count: Current attempt count for retries (starts at 1).
        trace_id: Trace id copied from the owning execution run.
        result_notification_id: Created notification id when action succeeded.
        error_kind: Sanitized failure kind.
        error_text: Sanitized + truncated failure text.
        created_at: Creation timestamp (UTC).
        updated_at: Update timestamp (UTC).
    """

    __tablename__ = "automation_action_executions"
    __table_args__ = (
        Index(
            "ix_automation_action_executions_run_id",
            "run_id",
        ),
        Index(
            "ix_automation_action_executions_status_updated_at",
            "status",
            "updated_at",
        ),
        Index(
            "ix_automation_action_executions_dedupe_key",
            "dedupe_key",
        ),
    )

    action_execution_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("automation_execution_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(36), nullable=False)
    recipient_staff_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    recipient_role: Mapped[str] = mapped_column(String(32), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    result_notification_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error_kind: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_text: Mapped[str | None] = mapped_column(String(1024), nullable=True)
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

