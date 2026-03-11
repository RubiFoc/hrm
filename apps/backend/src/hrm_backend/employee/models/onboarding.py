"""SQLAlchemy models for employee-domain onboarding workflow artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base
from hrm_backend.employee.utils.onboarding import (
    ONBOARDING_RUN_STATUS_STARTED,
    ONBOARDING_TASK_STATUS_PENDING,
)


class OnboardingRun(Base):
    """Minimal durable onboarding-start artifact created after employee bootstrap.

    Attributes:
        onboarding_id: Unique onboarding run identifier.
        employee_id: Employee profile identifier that owns this onboarding run.
        hire_conversion_id: Source hire-conversion identifier copied from the employee profile.
        status: Minimal onboarding lifecycle state for the current slice.
        started_at: Timestamp when onboarding was triggered.
        started_by_staff_id: Staff subject that triggered onboarding.
    """

    __tablename__ = "onboarding_runs"
    __table_args__ = (
        Index(
            "ux_onboarding_runs_employee",
            "employee_id",
            unique=True,
        ),
        Index("ix_onboarding_runs_status", "status"),
    )

    onboarding_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("employee_profiles.employee_id", ondelete="CASCADE"),
        nullable=False,
    )
    hire_conversion_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hire_conversions.conversion_id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ONBOARDING_RUN_STATUS_STARTED,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    started_by_staff_id: Mapped[str] = mapped_column(String(36), nullable=False)


class OnboardingTask(Base):
    """Materialized onboarding checklist task belonging to one onboarding run.

    Attributes:
        task_id: Unique onboarding task identifier.
        onboarding_id: Owning onboarding run identifier.
        template_id: Source onboarding template identifier captured for provenance.
        template_item_id: Source template item identifier captured for provenance.
        code: Stable task code copied from the template item.
        title: Short task title frozen at generation time.
        description: Optional task guidance text frozen at generation time.
        sort_order: Deterministic task ordering inside the onboarding run.
        is_required: Whether the task is mandatory by default.
        status: Current workflow state for task execution tracking.
        assigned_role: Optional role currently expected to own the task.
        assigned_staff_id: Optional staff subject explicitly assigned to the task.
        due_at: Optional staff-managed SLA timestamp.
        completed_at: Timestamp when the task last entered `completed` state.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "onboarding_tasks"
    __table_args__ = (
        Index(
            "ux_onboarding_tasks_onboarding_code",
            "onboarding_id",
            "code",
            unique=True,
        ),
        Index("ix_onboarding_tasks_onboarding", "onboarding_id"),
        Index("ix_onboarding_tasks_status", "status"),
        Index("ix_onboarding_tasks_due_at", "due_at"),
        Index("ix_onboarding_tasks_assigned_staff", "assigned_staff_id"),
    )

    task_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    onboarding_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("onboarding_runs.onboarding_id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[str] = mapped_column(String(36), nullable=False)
    template_item_id: Mapped[str] = mapped_column(String(36), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ONBOARDING_TASK_STATUS_PENDING,
    )
    assigned_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assigned_staff_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
