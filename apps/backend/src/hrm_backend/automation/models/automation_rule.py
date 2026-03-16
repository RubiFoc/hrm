"""Persistence model for automation rules."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class AutomationRule(Base):
    """One automation rule row evaluated on matching trigger events.

    Attributes:
        rule_id: Stable rule identifier.
        name: Human-readable name for operator/admin usage.
        trigger: Trigger event key.
        conditions_json: JSON condition tree evaluated against the event payload.
        actions_json: JSON list of action definitions (planned only in TASK-08-01).
        priority: Higher value means higher precedence when ordering rules.
        is_active: Whether the rule is eligible for evaluation.
        created_by_staff_id: Staff subject that created the rule.
        updated_by_staff_id: Staff subject that last updated the rule.
        created_at: Creation timestamp.
        updated_at: Update timestamp.
    """

    __tablename__ = "automation_rules"
    __table_args__ = (
        Index("ix_automation_rules_trigger_active_priority", "trigger", "is_active", "priority"),
        Index("ix_automation_rules_updated_at", "updated_at"),
    )

    rule_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    trigger: Mapped[str] = mapped_column(String(128), nullable=False)
    conditions_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    actions_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_staff_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
    updated_by_staff_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), nullable=False)
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
