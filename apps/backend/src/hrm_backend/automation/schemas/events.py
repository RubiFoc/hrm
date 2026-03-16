"""Trigger event schemas consumed by the automation evaluator."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from hrm_backend.rbac import Role

AutomationTrigger = Literal[
    "pipeline.transition_appended",
    "offer.status_changed",
    "onboarding.task_assigned",
]


class PipelineTransitionAppendedPayload(BaseModel):
    """Payload for the `pipeline.transition_appended` trigger."""

    model_config = ConfigDict(extra="forbid")

    transition_id: UUID
    vacancy_id: UUID
    vacancy_title: str = Field(min_length=1, max_length=256)
    candidate_id: UUID
    candidate_id_short: str = Field(min_length=4, max_length=32)
    from_stage: str | None = Field(default=None, min_length=1, max_length=32)
    to_stage: str = Field(min_length=1, max_length=32)
    stage: str = Field(min_length=1, max_length=32)
    hiring_manager_staff_id: UUID | None = None
    changed_by_staff_id: str = Field(min_length=1, max_length=128)
    changed_by_role: str = Field(min_length=1, max_length=64)


class OfferStatusChangedPayload(BaseModel):
    """Payload for the `offer.status_changed` trigger."""

    model_config = ConfigDict(extra="forbid")

    offer_id: UUID
    vacancy_id: UUID
    vacancy_title: str = Field(min_length=1, max_length=256)
    candidate_id: UUID
    candidate_id_short: str = Field(min_length=4, max_length=32)
    previous_status: str | None = Field(default=None, min_length=1, max_length=32)
    status: str = Field(min_length=1, max_length=32)
    offer_status: str = Field(min_length=1, max_length=32)
    hiring_manager_staff_id: UUID | None = None
    changed_by_staff_id: str = Field(min_length=1, max_length=128)
    changed_by_role: str = Field(min_length=1, max_length=64)


class OnboardingTaskAssignedPayload(BaseModel):
    """Payload for the `onboarding.task_assigned` trigger."""

    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    onboarding_id: UUID
    employee_id: UUID
    task_title: str = Field(min_length=1, max_length=256)
    assigned_role: Role | None = None
    assigned_staff_id: UUID | None = None
    previous_assigned_role: Role | None = None
    previous_assigned_staff_id: UUID | None = None
    due_at: datetime | None = None
    employee_full_name: str = Field(min_length=1, max_length=256)


class PipelineTransitionAppendedEvent(BaseModel):
    """Automation event envelope for `pipeline.transition_appended`."""

    model_config = ConfigDict(extra="forbid")

    event_type: Literal["pipeline.transition_appended"]
    event_time: datetime
    trigger_event_id: UUID
    payload: PipelineTransitionAppendedPayload


class OfferStatusChangedEvent(BaseModel):
    """Automation event envelope for `offer.status_changed`."""

    model_config = ConfigDict(extra="forbid")

    event_type: Literal["offer.status_changed"]
    event_time: datetime
    trigger_event_id: UUID
    payload: OfferStatusChangedPayload


class OnboardingTaskAssignedEvent(BaseModel):
    """Automation event envelope for `onboarding.task_assigned`."""

    model_config = ConfigDict(extra="forbid")

    event_type: Literal["onboarding.task_assigned"]
    event_time: datetime
    trigger_event_id: UUID
    payload: OnboardingTaskAssignedPayload


AutomationEvent = Annotated[
    PipelineTransitionAppendedEvent
    | OfferStatusChangedEvent
    | OnboardingTaskAssignedEvent,
    Field(discriminator="event_type"),
]
