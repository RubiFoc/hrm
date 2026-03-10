"""Schema models for interview scheduling and feedback APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

InterviewStatus = Literal[
    "pending_sync",
    "awaiting_candidate_confirmation",
    "confirmed",
    "reschedule_requested",
    "cancelled",
]
CalendarSyncStatus = Literal["queued", "running", "synced", "conflict", "failed"]
CandidateResponseStatus = Literal["pending", "confirmed", "reschedule_requested", "declined"]
InterviewLocationKind = Literal["google_meet", "onsite", "phone"]
CancelledBy = Literal["staff", "candidate"]
InterviewFeedbackRecommendation = Literal["strong_yes", "yes", "mixed", "no"]
InterviewFeedbackGateStatus = Literal["passed", "blocked"]


class InterviewCreateRequest(BaseModel):
    """Input payload for creating one interview schedule proposal."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: UUID
    scheduled_start_local: datetime
    scheduled_end_local: datetime
    timezone: str = Field(min_length=1, max_length=128)
    location_kind: InterviewLocationKind
    location_details: str | None = Field(default=None, max_length=2048)
    interviewer_staff_ids: list[UUID] = Field(min_length=1, max_length=16)

    @field_validator("scheduled_start_local", "scheduled_end_local")
    @classmethod
    def validate_naive_local_datetimes(cls, value: datetime) -> datetime:
        """Ensure local schedule inputs stay timezone-naive."""
        if value.tzinfo is not None:
            raise ValueError("scheduled local datetimes must not contain timezone offsets")
        return value


class InterviewRescheduleRequest(BaseModel):
    """Input payload for replacing one existing interview schedule."""

    model_config = ConfigDict(extra="forbid")

    scheduled_start_local: datetime
    scheduled_end_local: datetime
    timezone: str = Field(min_length=1, max_length=128)
    location_kind: InterviewLocationKind
    location_details: str | None = Field(default=None, max_length=2048)
    interviewer_staff_ids: list[UUID] = Field(min_length=1, max_length=16)

    @field_validator("scheduled_start_local", "scheduled_end_local")
    @classmethod
    def validate_naive_local_datetimes(cls, value: datetime) -> datetime:
        """Ensure local schedule inputs stay timezone-naive."""
        if value.tzinfo is not None:
            raise ValueError("scheduled local datetimes must not contain timezone offsets")
        return value


class InterviewCancelRequest(BaseModel):
    """Input payload for staff-triggered interview cancellation."""

    model_config = ConfigDict(extra="forbid")

    cancel_reason_code: str = Field(min_length=1, max_length=128)


class PublicInterviewActionRequest(BaseModel):
    """Optional note payload for public candidate interview actions."""

    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=1000)


class InterviewFeedbackUpsertRequest(BaseModel):
    """Input payload for current-user interview feedback create or update."""

    model_config = ConfigDict(extra="forbid")

    requirements_match_score: int = Field(ge=1, le=5)
    communication_score: int = Field(ge=1, le=5)
    problem_solving_score: int = Field(ge=1, le=5)
    collaboration_score: int = Field(ge=1, le=5)
    recommendation: InterviewFeedbackRecommendation
    strengths_note: str = Field(min_length=1, max_length=4000)
    concerns_note: str = Field(min_length=1, max_length=4000)
    evidence_note: str = Field(min_length=1, max_length=4000)

    @field_validator("strengths_note", "concerns_note", "evidence_note")
    @classmethod
    def validate_non_blank_notes(cls, value: str) -> str:
        """Trim note payloads and reject whitespace-only values."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("feedback notes must not be blank")
        return normalized


class InterviewFeedbackItemResponse(BaseModel):
    """Structured feedback row for one interviewer and one schedule version."""

    feedback_id: UUID
    interview_id: UUID
    schedule_version: int
    interviewer_staff_id: UUID
    requirements_match_score: int
    communication_score: int
    problem_solving_score: int
    collaboration_score: int
    recommendation: InterviewFeedbackRecommendation
    strengths_note: str
    concerns_note: str
    evidence_note: str
    submitted_at: datetime
    updated_at: datetime


class InterviewFeedbackRecommendationDistributionResponse(BaseModel):
    """Distribution of structured recommendations in the current interview panel."""

    strong_yes: int
    yes: int
    mixed: int
    no: int


class InterviewFeedbackAverageScoresResponse(BaseModel):
    """Average rubric scores for the current interview panel."""

    requirements_match_score: float | None
    communication_score: float | None
    problem_solving_score: float | None
    collaboration_score: float | None


class InterviewFeedbackPanelSummaryResponse(BaseModel):
    """Current-version panel summary used by HR fairness review and interviewer UX."""

    interview_id: UUID
    vacancy_id: UUID
    candidate_id: UUID
    schedule_version: int
    required_interviewer_ids: list[UUID]
    submitted_interviewer_ids: list[UUID]
    missing_interviewer_ids: list[UUID]
    required_interviewer_count: int
    submitted_count: int
    gate_status: InterviewFeedbackGateStatus
    gate_reason_codes: list[str]
    recommendation_distribution: InterviewFeedbackRecommendationDistributionResponse
    average_scores: InterviewFeedbackAverageScoresResponse
    items: list[InterviewFeedbackItemResponse]


class HRInterviewResponse(BaseModel):
    """Canonical HR-facing interview payload."""

    interview_id: UUID
    vacancy_id: UUID
    candidate_id: UUID
    status: InterviewStatus
    calendar_sync_status: CalendarSyncStatus
    schedule_version: int
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    timezone: str
    location_kind: InterviewLocationKind
    location_details: str | None
    interviewer_staff_ids: list[UUID]
    candidate_response_status: CandidateResponseStatus
    candidate_response_note: str | None
    candidate_token_expires_at: datetime | None
    candidate_invite_url: str | None
    calendar_event_id: str | None
    last_synced_at: datetime | None
    cancelled_by: CancelledBy | None
    cancel_reason_code: str | None
    created_at: datetime
    updated_at: datetime


class HRInterviewListResponse(BaseModel):
    """List payload for HR-facing interview reads."""

    items: list[HRInterviewResponse]


class PublicInterviewRegistrationResponse(BaseModel):
    """Public candidate-facing interview registration payload."""

    interview_id: UUID
    vacancy_id: UUID
    vacancy_title: str
    status: InterviewStatus
    calendar_sync_status: CalendarSyncStatus
    schedule_version: int
    scheduled_start_at: datetime
    scheduled_end_at: datetime
    timezone: str
    location_kind: InterviewLocationKind
    location_details: str | None
    candidate_response_status: CandidateResponseStatus
    candidate_response_note: str | None
    candidate_token_expires_at: datetime | None
    cancelled_by: CancelledBy | None
    cancel_reason_code: str | None
    updated_at: datetime
