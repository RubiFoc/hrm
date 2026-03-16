"""Rule CRUD schemas for automation management APIs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from hrm_backend.automation.schemas.actions import AutomationAction
from hrm_backend.automation.schemas.conditions import AutomationCondition
from hrm_backend.automation.schemas.events import AutomationTrigger


class AutomationRuleCreateRequest(BaseModel):
    """Create request payload for automation rules."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    trigger: AutomationTrigger
    conditions: AutomationCondition | None = None
    actions: list[AutomationAction] = Field(min_length=1)
    priority: int = Field(default=0)


class AutomationRuleUpdateRequest(BaseModel):
    """Patch request payload for automation rules (excluding activation)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=128)
    conditions: AutomationCondition | None = None
    actions: list[AutomationAction] | None = Field(default=None, min_length=1)
    priority: int | None = None


class AutomationRuleActivationRequest(BaseModel):
    """Activation toggle payload for automation rules."""

    model_config = ConfigDict(extra="forbid")

    is_active: bool


class AutomationRuleResponse(BaseModel):
    """Public API representation of an automation rule."""

    model_config = ConfigDict(extra="forbid")

    rule_id: UUID
    name: str
    trigger: AutomationTrigger
    conditions: dict[str, object] | None
    actions: list[dict[str, object]]
    priority: int
    is_active: bool
    created_by_staff_id: UUID
    updated_by_staff_id: UUID
    created_at: datetime
    updated_at: datetime


class AutomationRuleListResponse(BaseModel):
    """List response for automation rules."""

    model_config = ConfigDict(extra="forbid")

    items: list[AutomationRuleResponse]

