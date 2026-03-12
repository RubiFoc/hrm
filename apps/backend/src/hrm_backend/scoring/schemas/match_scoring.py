"""API request and response schemas for match scoring endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MatchScoringStatus = Literal["queued", "running", "succeeded", "failed"]
MatchScoreManualReviewReason = Literal["low_confidence"]


class MatchScoreCreateRequest(BaseModel):
    """Input payload for explicit scoring request."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: UUID


class MatchScoreEvidenceResponse(BaseModel):
    """One evidence item returned to the HR shortlist review UI."""

    model_config = ConfigDict(extra="forbid")

    requirement: str
    snippet: str
    source_field: str | None = None


class MatchScoreResponse(BaseModel):
    """UI-ready latest score/status payload for one vacancy and candidate."""

    model_config = ConfigDict(extra="forbid")

    vacancy_id: UUID
    candidate_id: UUID
    status: MatchScoringStatus
    score: float | None = Field(default=None)
    confidence: float | None = Field(default=None)
    requires_manual_review: bool = Field(default=False)
    manual_review_reason: MatchScoreManualReviewReason | None = Field(default=None)
    confidence_threshold: float | None = Field(default=None)
    summary: str | None = Field(default=None)
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    evidence: list[MatchScoreEvidenceResponse] = Field(default_factory=list)
    scored_at: datetime | None = Field(default=None)
    model_name: str | None = Field(default=None)
    model_version: str | None = Field(default=None)


class MatchScoreListResponse(BaseModel):
    """List of latest score/status payloads for one vacancy."""

    model_config = ConfigDict(extra="forbid")

    items: list[MatchScoreResponse]
