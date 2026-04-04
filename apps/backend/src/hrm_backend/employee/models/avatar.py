"""Persistence model for employee profile avatars."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class EmployeeProfileAvatar(Base):
    """Stored metadata for employee profile avatars.

    Attributes:
        avatar_id: Unique avatar identifier.
        employee_id: Employee profile identifier owning the avatar.
        object_key: Object storage key in MinIO bucket.
        mime_type: Validated avatar MIME type.
        size_bytes: Uploaded avatar size in bytes.
        is_active: Whether this avatar is currently active for the employee profile.
        updated_at: Timestamp of the latest avatar update/deactivation.
    """

    __tablename__ = "employee_profile_avatars"
    __table_args__ = (
        Index("ix_employee_profile_avatars_employee_id", "employee_id"),
        Index("ix_employee_profile_avatars_object_key", "object_key", unique=True),
        Index("ix_employee_profile_avatars_employee_active", "employee_id", "is_active"),
    )

    avatar_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("employee_profiles.employee_id", ondelete="CASCADE"),
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
