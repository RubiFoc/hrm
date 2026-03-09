"""Schema models for interview scheduling APIs."""

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
