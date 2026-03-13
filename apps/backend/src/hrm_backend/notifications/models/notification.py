"""Persistence model for in-app notifications."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class Notification(Base):
    """In-app notification row scoped to one recipient staff account.

    Attributes:
        notification_id: Unique notification identifier.
        recipient_staff_id: Recipient staff-account subject.
        recipient_role: Recipient role snapshot captured at emit time.
        kind: Stable notification kind used by frontend rendering.
        source_type: Domain source category such as `vacancy` or `onboarding_task`.
        source_id: Domain source identifier used for later correlation.
        dedupe_key: Event fingerprint unique within one recipient scope.
        title: Short human-readable notification title.
        body: Human-readable notification message body.
        payload_json: Additive structured payload used by frontend workspaces.
        created_at: Notification creation timestamp.
        read_at: Acknowledgement timestamp when the recipient marks the item as read.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "recipient_staff_id",
            "dedupe_key",
            name="ux_notifications_recipient_dedupe",
        ),
        Index(
            "ix_notifications_recipient_created_at",
            "recipient_staff_id",
            "created_at",
        ),
        Index(
            "ix_notifications_recipient_read_at",
            "recipient_staff_id",
            "read_at",
        ),
    )

    notification_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    recipient_staff_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("staff_accounts.staff_id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_role: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
