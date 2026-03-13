"""Request, response, and internal payloads for in-app notifications."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from hrm_backend.rbac import Role


class NotificationPayload(BaseModel):
    """Structured additive notification payload exposed to frontend workspaces."""

    model_config = ConfigDict(extra="forbid")

    vacancy_id: UUID | None = None
    onboarding_id: UUID | None = None
    task_id: UUID | None = None
    employee_id: UUID | None = None
    vacancy_title: str | None = Field(default=None, max_length=256)
    task_title: str | None = Field(default=None, max_length=256)
    employee_full_name: str | None = Field(default=None, max_length=256)
    due_at: datetime | None = None


class NotificationCreate(BaseModel):
    """Internal service payload used to persist one notification row."""

    model_config = ConfigDict(extra="forbid")

    recipient_staff_id: UUID
    recipient_role: Role
    kind: str = Field(min_length=1, max_length=64)
    source_type: str = Field(min_length=1, max_length=64)
    source_id: UUID
    dedupe_key: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(min_length=1)
    payload: NotificationPayload = Field(default_factory=NotificationPayload)


class NotificationResponse(BaseModel):
    """API representation of one in-app notification."""

    notification_id: UUID
    recipient_staff_id: UUID
    recipient_role: Role
    kind: str
    source_type: str
    source_id: UUID
    status: str
    title: str
    body: str
    payload: NotificationPayload
    created_at: datetime
    read_at: datetime | None


class NotificationListResponse(BaseModel):
    """Paginated notification list scoped to the current authenticated recipient."""

    items: list[NotificationResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    unread_count: int = Field(ge=0)


class NotificationDigestSummaryResponse(BaseModel):
    """Server-computed summary counters for the current notification workspace."""

    unread_notification_count: int = Field(ge=0)
    active_task_count: int = Field(ge=0)
    overdue_task_count: int = Field(ge=0)
    owned_open_vacancy_count: int = Field(ge=0)


class NotificationDigestResponse(BaseModel):
    """On-demand digest payload for the current authenticated recipient."""

    generated_at: datetime
    summary: NotificationDigestSummaryResponse
    latest_unread_items: list[NotificationResponse]
