"""Pure feedback-summary and fairness-gate helpers for interview workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from hrm_backend.interviews.models.feedback import InterviewFeedback
from hrm_backend.interviews.models.interview import Interview

RECOMMENDATION_VALUES: tuple[str, ...] = ("strong_yes", "yes", "mixed", "no")
GATE_REASON_WINDOW_NOT_OPEN = "interview_feedback_window_not_open"
GATE_REASON_MISSING = "interview_feedback_missing"
GATE_REASON_INCOMPLETE = "interview_feedback_incomplete"
GATE_REASON_STALE = "interview_feedback_stale"


@dataclass(frozen=True)
class InterviewFeedbackPanelSummaryData:
    """Derived current-version summary used by APIs and fairness gate checks."""

    current_items: tuple[InterviewFeedback, ...]
    required_interviewer_ids: tuple[str, ...]
    submitted_interviewer_ids: tuple[str, ...]
    missing_interviewer_ids: tuple[str, ...]
    gate_status: str
    gate_reason_codes: tuple[str, ...]
    recommendation_distribution: dict[str, int]
    average_scores: dict[str, float | None]


def build_feedback_panel_summary(
    *,
    interview: Interview,
    feedback_history: list[InterviewFeedback],
    now: datetime | None = None,
) -> InterviewFeedbackPanelSummaryData:
    """Build current-version feedback summary and fairness gate evaluation.

    Args:
        interview: Current interview row.
        feedback_history: Feedback rows for the interview across all schedule versions.
        now: Optional override for current UTC timestamp.

    Returns:
        InterviewFeedbackPanelSummaryData: Derived current-version summary.
    """
    resolved_now = now or datetime.now(UTC)
    current_version = interview.schedule_version
    current_items = tuple(
        sorted(
            (
                item
                for item in feedback_history
                if item.schedule_version == current_version
            ),
            key=lambda item: (item.interviewer_staff_id, item.feedback_id),
        )
    )
    required_interviewer_ids = tuple(sorted(interview.interviewer_staff_ids_json))
    current_by_interviewer = {
        item.interviewer_staff_id: item
        for item in current_items
        if item.interviewer_staff_id in required_interviewer_ids
    }
    submitted_interviewer_ids = tuple(sorted(current_by_interviewer))
    historical_versions = {
        interviewer_id: max(
            (
                item.schedule_version
                for item in feedback_history
                if item.interviewer_staff_id == interviewer_id
            ),
            default=None,
        )
        for interviewer_id in required_interviewer_ids
    }
    missing_interviewer_ids = tuple(
        interviewer_id
        for interviewer_id in required_interviewer_ids
        if interviewer_id not in current_by_interviewer
    )
    stale_interviewer_ids = tuple(
        interviewer_id
        for interviewer_id in missing_interviewer_ids
        if historical_versions.get(interviewer_id) not in (None, current_version)
    )
    missing_without_history = tuple(
        interviewer_id
        for interviewer_id in missing_interviewer_ids
        if interviewer_id not in stale_interviewer_ids
    )
    incomplete_interviewer_ids = tuple(
        interviewer_id
        for interviewer_id, item in current_by_interviewer.items()
        if not is_feedback_complete(item)
    )

    gate_reason_codes: list[str] = []
    if _ensure_aware_utc(interview.scheduled_end_at) > resolved_now:
        gate_reason_codes.append(GATE_REASON_WINDOW_NOT_OPEN)
    else:
        if stale_interviewer_ids:
            gate_reason_codes.append(GATE_REASON_STALE)
        if missing_without_history:
            gate_reason_codes.append(GATE_REASON_MISSING)
        if incomplete_interviewer_ids:
            gate_reason_codes.append(GATE_REASON_INCOMPLETE)

    recommendation_distribution = {item: 0 for item in RECOMMENDATION_VALUES}
    for item in current_items:
        if item.recommendation in recommendation_distribution:
            recommendation_distribution[item.recommendation] += 1

    average_scores = {
        "requirements_match_score": _average_score(
            item.requirements_match_score for item in current_items
        ),
        "communication_score": _average_score(item.communication_score for item in current_items),
        "problem_solving_score": _average_score(
            item.problem_solving_score for item in current_items
        ),
        "collaboration_score": _average_score(item.collaboration_score for item in current_items),
    }

    return InterviewFeedbackPanelSummaryData(
        current_items=current_items,
        required_interviewer_ids=required_interviewer_ids,
        submitted_interviewer_ids=submitted_interviewer_ids,
        missing_interviewer_ids=missing_interviewer_ids,
        gate_status="passed" if not gate_reason_codes else "blocked",
        gate_reason_codes=tuple(gate_reason_codes),
        recommendation_distribution=recommendation_distribution,
        average_scores=average_scores,
    )


def is_feedback_complete(item: InterviewFeedback) -> bool:
    """Return whether one persisted feedback row satisfies gate completeness rules.

    Args:
        item: Persisted interview feedback row.

    Returns:
        bool: `True` when the row is complete and valid for fairness gate purposes.
    """
    return (
        _is_valid_score(item.requirements_match_score)
        and _is_valid_score(item.communication_score)
        and _is_valid_score(item.problem_solving_score)
        and _is_valid_score(item.collaboration_score)
        and item.recommendation in RECOMMENDATION_VALUES
        and bool(item.strengths_note.strip())
        and bool(item.concerns_note.strip())
        and bool(item.evidence_note.strip())
    )


def _is_valid_score(value: int) -> bool:
    """Return whether one rubric score stays inside the allowed `1..5` range."""
    return 1 <= value <= 5


def _average_score(values) -> float | None:
    """Compute one rounded average score from an iterable of integer values."""
    materialized = [value for value in values if _is_valid_score(value)]
    if not materialized:
        return None
    return round(sum(materialized) / len(materialized), 2)


def _ensure_aware_utc(value: datetime) -> datetime:
    """Normalize potentially naive persisted timestamps to aware UTC values."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
