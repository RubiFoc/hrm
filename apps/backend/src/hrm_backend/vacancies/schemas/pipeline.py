"""Pipeline transition request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PipelineStage = Literal[
    "applied",
    "screening",
    "shortlist",
    "interview",
    "offer",
    "hired",
    "rejected",
]


class PipelineTransitionCreateRequest(BaseModel):
    """Input payload for one pipeline transition append event."""

    model_config = ConfigDict(extra="forbid")

    vacancy_id: UUID
    candidate_id: UUID
    to_stage: PipelineStage
    reason: str | None = Field(default=None, max_length=2048)


class PipelineTransitionResponse(BaseModel):
    """Pipeline transition API representation."""

    transition_id: UUID
    vacancy_id: UUID
    candidate_id: UUID
    from_stage: PipelineStage | None
    to_stage: PipelineStage
    reason: str | None
    changed_by_sub: str
    changed_by_role: str
    transitioned_at: datetime


class PipelineTransitionListResponse(BaseModel):
    """Ordered pipeline transition history payload for one vacancy+candidate pair."""

    items: list[PipelineTransitionResponse]
