"""SQLAlchemy models for onboarding checklist template persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class OnboardingTemplate(Base):
    """Configurable onboarding checklist template managed by staff users.

    Attributes:
        template_id: Unique onboarding checklist template identifier.
        name: Human-readable unique template name.
        description: Optional template guidance text.
        is_active: Whether this template is the current active default for later task generation.
        created_by_staff_id: Staff subject that created the template.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "onboarding_templates"
    __table_args__ = (
        Index("ux_onboarding_templates_name", "name", unique=True),
        Index("ix_onboarding_templates_is_active", "is_active"),
    )

    template_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_staff_id: Mapped[str] = mapped_column(String(36), nullable=False)
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


class OnboardingTemplateItem(Base):
    """Checklist item definition belonging to one onboarding template.

    Attributes:
        template_item_id: Unique template item identifier.
        template_id: Owning onboarding template identifier.
        code: Stable item code used by later task-generation slices.
        title: Short checklist item title.
        description: Optional item guidance text.
        sort_order: Display and generation order inside the template.
        is_required: Whether the later generated task is mandatory by default.
    """

    __tablename__ = "onboarding_template_items"
    __table_args__ = (
        Index(
            "ux_onboarding_template_items_code",
            "template_id",
            "code",
            unique=True,
        ),
        Index(
            "ux_onboarding_template_items_sort_order",
            "template_id",
            "sort_order",
            unique=True,
        ),
    )

    template_item_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    template_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("onboarding_templates.template_id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
