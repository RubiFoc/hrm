"""Lifecycle rules for interview scheduling and public registration."""

from __future__ import annotations

from hrm_backend.interviews.schemas.interview import InterviewStatus

ACTIVE_INTERVIEW_STATUSES: frozenset[InterviewStatus] = frozenset(
    {
        "pending_sync",
        "awaiting_candidate_confirmation",
        "confirmed",
        "reschedule_requested",
    }
)


def is_active_interview_status(status: InterviewStatus) -> bool:
    """Return whether one interview status is considered active."""
    return status in ACTIVE_INTERVIEW_STATUSES


def can_hr_reschedule(status: InterviewStatus) -> bool:
    """Return whether HR can reschedule an interview from current status."""
    return status in ACTIVE_INTERVIEW_STATUSES


def can_hr_cancel(status: InterviewStatus) -> bool:
    """Return whether HR can cancel an interview from current status."""
    return status in ACTIVE_INTERVIEW_STATUSES


def can_candidate_confirm(status: InterviewStatus) -> bool:
    """Return whether public candidate can confirm the current schedule."""
    return status == "awaiting_candidate_confirmation"


def can_candidate_request_reschedule(status: InterviewStatus) -> bool:
    """Return whether public candidate can request a new slot."""
    return status in {"awaiting_candidate_confirmation", "confirmed"}


def can_candidate_cancel(status: InterviewStatus) -> bool:
    """Return whether public candidate can decline the current interview."""
    return status in {"awaiting_candidate_confirmation", "confirmed"}
