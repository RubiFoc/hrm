"""Unit tests for interview feedback summary and fairness gate helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hrm_backend.interviews.models.feedback import InterviewFeedback
from hrm_backend.interviews.models.interview import Interview
from hrm_backend.interviews.utils.feedback import (
    GATE_REASON_INCOMPLETE,
    GATE_REASON_MISSING,
    GATE_REASON_STALE,
    GATE_REASON_WINDOW_NOT_OPEN,
    build_feedback_panel_summary,
)

INTERVIEWER_A = "11111111-1111-4111-8111-111111111111"
INTERVIEWER_B = "22222222-2222-4222-8222-222222222222"
INTERVIEWER_C = "33333333-3333-4333-8333-333333333333"


def test_summary_blocks_feedback_before_interview_window_closes() -> None:
    """Window-not-open must block fairness gate even if panel feedback is complete."""
    now = datetime.now(UTC)
    interview = _build_interview(
        schedule_version=1,
        scheduled_end_at=now + timedelta(hours=1),
        interviewer_staff_ids=[INTERVIEWER_A, INTERVIEWER_B],
    )
    summary = build_feedback_panel_summary(
        interview=interview,
        feedback_history=[
            _build_feedback(interviewer_staff_id=INTERVIEWER_A, schedule_version=1),
            _build_feedback(interviewer_staff_id=INTERVIEWER_B, schedule_version=1),
        ],
        now=now,
    )

    assert summary.gate_status == "blocked"
    assert summary.gate_reason_codes == (GATE_REASON_WINDOW_NOT_OPEN,)


def test_summary_marks_stale_missing_and_incomplete_feedback() -> None:
    """Summary must distinguish stale, never-submitted, and incomplete feedback cases."""
    now = datetime.now(UTC)
    interview = _build_interview(
        schedule_version=2,
        scheduled_end_at=now - timedelta(minutes=10),
        interviewer_staff_ids=[INTERVIEWER_A, INTERVIEWER_B, INTERVIEWER_C],
    )
    summary = build_feedback_panel_summary(
        interview=interview,
        feedback_history=[
            _build_feedback(interviewer_staff_id=INTERVIEWER_A, schedule_version=1),
            _build_feedback(
                interviewer_staff_id=INTERVIEWER_C,
                schedule_version=2,
                evidence_note="   ",
            ),
        ],
        now=now,
    )

    assert summary.gate_status == "blocked"
    assert summary.submitted_interviewer_ids == (INTERVIEWER_C,)
    assert summary.missing_interviewer_ids == (INTERVIEWER_A, INTERVIEWER_B)
    assert summary.gate_reason_codes == (
        GATE_REASON_STALE,
        GATE_REASON_MISSING,
        GATE_REASON_INCOMPLETE,
    )


def test_summary_passes_with_complete_current_panel_feedback() -> None:
    """Complete current-version panel feedback must pass the fairness gate."""
    now = datetime.now(UTC)
    interview = _build_interview(
        schedule_version=3,
        scheduled_end_at=now - timedelta(hours=2),
        interviewer_staff_ids=[INTERVIEWER_A, INTERVIEWER_B],
    )
    summary = build_feedback_panel_summary(
        interview=interview,
        feedback_history=[
            _build_feedback(
                interviewer_staff_id=INTERVIEWER_A,
                schedule_version=3,
                requirements_match_score=5,
                communication_score=4,
                problem_solving_score=5,
                collaboration_score=4,
                recommendation="strong_yes",
            ),
            _build_feedback(
                interviewer_staff_id=INTERVIEWER_B,
                schedule_version=3,
                requirements_match_score=3,
                communication_score=4,
                problem_solving_score=4,
                collaboration_score=5,
                recommendation="yes",
            ),
        ],
        now=now,
    )

    assert summary.gate_status == "passed"
    assert summary.gate_reason_codes == ()
    assert summary.submitted_interviewer_ids == (INTERVIEWER_A, INTERVIEWER_B)
    assert summary.recommendation_distribution == {
        "strong_yes": 1,
        "yes": 1,
        "mixed": 0,
        "no": 0,
    }
    assert summary.average_scores["requirements_match_score"] == 4.0
    assert summary.average_scores["communication_score"] == 4.0
    assert summary.average_scores["problem_solving_score"] == 4.5
    assert summary.average_scores["collaboration_score"] == 4.5


def _build_interview(
    *,
    schedule_version: int,
    scheduled_end_at: datetime,
    interviewer_staff_ids: list[str],
) -> Interview:
    """Build interview row fixture for pure summary tests."""
    scheduled_start_at = scheduled_end_at - timedelta(hours=1)
    return Interview(
        interview_id="99999999-9999-4999-8999-999999999999",
        vacancy_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        candidate_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        status="awaiting_candidate_confirmation",
        calendar_sync_status="synced",
        schedule_version=schedule_version,
        scheduled_start_at=scheduled_start_at,
        scheduled_end_at=scheduled_end_at,
        timezone="UTC",
        location_kind="google_meet",
        location_details=None,
        interviewer_staff_ids_json=interviewer_staff_ids,
        calendar_event_id=None,
        candidate_token_nonce=None,
        candidate_token_hash=None,
        candidate_token_expires_at=None,
        candidate_response_status="pending",
        candidate_response_note=None,
        cancelled_by=None,
        cancel_reason_code=None,
        calendar_sync_reason_code=None,
        calendar_sync_error_detail=None,
        created_by_staff_id=INTERVIEWER_A,
        updated_by_staff_id=INTERVIEWER_A,
        created_at=scheduled_start_at - timedelta(days=1),
        updated_at=scheduled_start_at - timedelta(days=1),
        last_synced_at=scheduled_start_at - timedelta(days=1),
    )


def _build_feedback(
    *,
    interviewer_staff_id: str,
    schedule_version: int,
    requirements_match_score: int = 4,
    communication_score: int = 4,
    problem_solving_score: int = 4,
    collaboration_score: int = 4,
    recommendation: str = "yes",
    strengths_note: str = "Strong delivery discipline.",
    concerns_note: str = "Needs onboarding support.",
    evidence_note: str = "Explained recent production incidents clearly.",
) -> InterviewFeedback:
    """Build one interview feedback row fixture for summary tests."""
    submitted_at = datetime.now(UTC) - timedelta(minutes=5)
    return InterviewFeedback(
        feedback_id=f"feedback-{interviewer_staff_id[-4:]}-{schedule_version}",
        interview_id="99999999-9999-4999-8999-999999999999",
        schedule_version=schedule_version,
        interviewer_staff_id=interviewer_staff_id,
        requirements_match_score=requirements_match_score,
        communication_score=communication_score,
        problem_solving_score=problem_solving_score,
        collaboration_score=collaboration_score,
        recommendation=recommendation,
        strengths_note=strengths_note,
        concerns_note=concerns_note,
        evidence_note=evidence_note,
        submitted_at=submitted_at,
        updated_at=submitted_at,
    )
