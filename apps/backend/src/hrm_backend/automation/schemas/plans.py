"""Planned action schemas produced by the automation evaluator."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from hrm_backend.notifications.schemas.notification import NotificationPayload
from hrm_backend.rbac import Role


class PlannedNotificationEmitAction(BaseModel):
    """Deterministic notification action planned by a rule evaluation run."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(default="notification.emit", frozen=True)
    rule_id: UUID
    trigger_event_id: UUID
    event_time: datetime
    recipient_staff_id: UUID
    recipient_role: Role
    notification_kind: str = Field(min_length=1, max_length=64)
    source_type: str = Field(min_length=1, max_length=64)
    source_id: UUID
    dedupe_key: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(min_length=1)
    payload: NotificationPayload

