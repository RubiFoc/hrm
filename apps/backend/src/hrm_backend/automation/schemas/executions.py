"""API schemas for durable automation execution logs (TASK-08-03)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

AutomationExecutionRunStatus = Literal["running", "succeeded", "failed"]
AutomationActionExecutionStatus = Literal["succeeded", "deduped", "failed"]


class AutomationExecutionRunListItem(BaseModel):
    """Lightweight execution run payload for list views."""

    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    event_type: str = Field(min_length=1, max_length=128)
    trigger_event_id: UUID
    event_time: datetime
    correlation_id: str | None = Field(default=None, max_length=64)
    trace_id: str = Field(min_length=1, max_length=64)
    status: AutomationExecutionRunStatus
    planned_action_count: int = Field(ge=0)
    succeeded_action_count: int = Field(ge=0)
    deduped_action_count: int = Field(ge=0)
    failed_action_count: int = Field(ge=0)
    started_at: datetime
    finished_at: datetime | None


class AutomationExecutionRunResponse(AutomationExecutionRunListItem):
    """Full execution run response payload."""

    error_kind: str | None = Field(default=None, max_length=128)
    error_text: str | None = Field(default=None, max_length=1024)
    updated_at: datetime


class AutomationExecutionRunListResponse(BaseModel):
    """Paginated list response for execution runs."""

    model_config = ConfigDict(extra="forbid")

    items: list[AutomationExecutionRunListItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class AutomationActionExecutionListItem(BaseModel):
    """Lightweight action execution payload for list views."""

    model_config = ConfigDict(extra="forbid")

    action_execution_id: UUID
    run_id: UUID
    action: str = Field(min_length=1, max_length=64)
    rule_id: UUID
    recipient_staff_id: UUID
    recipient_role: str = Field(min_length=1, max_length=32)
    source_type: str = Field(min_length=1, max_length=64)
    source_id: UUID
    dedupe_key: str = Field(min_length=1, max_length=255)
    status: AutomationActionExecutionStatus
    attempt_count: int = Field(ge=1)
    trace_id: str = Field(min_length=1, max_length=64)
    result_notification_id: UUID | None
    error_kind: str | None = Field(default=None, max_length=128)
    created_at: datetime
    updated_at: datetime


class AutomationActionExecutionResponse(AutomationActionExecutionListItem):
    """Full action execution response payload."""

    error_text: str | None = Field(default=None, max_length=1024)


class AutomationActionExecutionListResponse(BaseModel):
    """Paginated list response for action executions."""

    model_config = ConfigDict(extra="forbid")

    items: list[AutomationActionExecutionListItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)

