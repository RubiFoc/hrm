"""Action definitions supported by automation rules (planning only in TASK-08-01)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NotificationEmitAction(BaseModel):
    """Plan an in-app notification emission (no execution in TASK-08-01)."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["notification.emit"]
    notification_kind: str = Field(min_length=1, max_length=64)
    title_template: str = Field(min_length=1, max_length=256)
    body_template: str = Field(min_length=1)
    payload_template: dict[str, object] = Field(default_factory=dict)


AutomationAction = NotificationEmitAction
