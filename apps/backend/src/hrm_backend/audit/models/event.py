"""Audit event persistence model."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class AuditEvent(Base):
    """Append-only audit event persisted for sensitive operations.

    Attributes:
        event_id: Event identifier (UUID string).
        occurred_at: Event creation timestamp in UTC.
        source: Event source (`api` or `job`).
        actor_sub: Subject identifier for actor, if available.
        actor_role: Actor role claim, if available.
        action: Action identifier (`auth.login`, `vacancy:create`, etc.).
        resource_type: Resource category affected by action.
        resource_id: Optional concrete resource identifier.
        result: Action result (`allowed`, `denied`, `success`, `failure`).
        reason: Optional human-readable reason for failures/denials.
        before_snapshot_json: Optional structured snapshot before a write operation.
        after_snapshot_json: Optional structured snapshot after a write operation.
        correlation_id: Trace identifier linked to request/job execution.
        ip: Caller IP for API-originated actions.
        user_agent: Caller user-agent for API-originated actions.
    """

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_occurred_at", "occurred_at"),
        Index("ix_audit_events_actor_sub", "actor_sub"),
        Index("ix_audit_events_action_result", "action", "result"),
        Index("ix_audit_events_correlation_id", "correlation_id"),
    )

    event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_sub: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_snapshot_json: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    after_snapshot_json: Mapped[dict[str, object] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
