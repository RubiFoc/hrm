"""Unit tests for interview lifecycle rules and schedule normalization."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import HTTPException

from hrm_backend.interviews.utils.lifecycle import (
    can_candidate_cancel,
    can_candidate_confirm,
    can_candidate_request_reschedule,
    can_hr_cancel,
    can_hr_reschedule,
    is_active_interview_status,
)
from hrm_backend.interviews.utils.scheduling import normalize_schedule_window


def test_lifecycle_helpers_match_planned_status_matrix() -> None:
    """Verify HR and candidate actions follow the planned interview status matrix."""
    assert is_active_interview_status("pending_sync") is True
    assert is_active_interview_status("awaiting_candidate_confirmation") is True
    assert is_active_interview_status("confirmed") is True
    assert is_active_interview_status("reschedule_requested") is True
    assert is_active_interview_status("cancelled") is False

    assert can_hr_reschedule("pending_sync") is True
    assert can_hr_reschedule("confirmed") is True
    assert can_hr_reschedule("cancelled") is False
    assert can_hr_cancel("awaiting_candidate_confirmation") is True
    assert can_hr_cancel("cancelled") is False

    assert can_candidate_confirm("awaiting_candidate_confirmation") is True
    assert can_candidate_confirm("confirmed") is False
    assert can_candidate_request_reschedule("awaiting_candidate_confirmation") is True
    assert can_candidate_request_reschedule("confirmed") is True
    assert can_candidate_request_reschedule("reschedule_requested") is False
    assert can_candidate_cancel("awaiting_candidate_confirmation") is True
    assert can_candidate_cancel("confirmed") is True
    assert can_candidate_cancel("cancelled") is False


def test_normalize_schedule_window_converts_local_values_to_utc() -> None:
    """Verify local wall-clock input is stored as UTC while preserving configured timezone."""
    start_at, end_at, timezone_name = normalize_schedule_window(
        scheduled_start_local=datetime(2026, 3, 12, 10, 0, 0),
        scheduled_end_local=datetime(2026, 3, 12, 11, 0, 0),
        timezone_name="Europe/Minsk",
    )

    assert timezone_name == "Europe/Minsk"
    assert start_at.isoformat() == "2026-03-12T07:00:00+00:00"
    assert end_at.isoformat() == "2026-03-12T08:00:00+00:00"


@pytest.mark.parametrize(
    ("timezone_name", "start_at", "end_at", "detail"),
    [
        ("", datetime(2026, 3, 12, 10, 0, 0), datetime(2026, 3, 12, 11, 0, 0), "invalid_timezone"),
        (
            "Missing/Timezone",
            datetime(2026, 3, 12, 10, 0, 0),
            datetime(2026, 3, 12, 11, 0, 0),
            "invalid_timezone",
        ),
        (
            "Europe/Minsk",
            datetime(2026, 3, 12, 11, 0, 0),
            datetime(2026, 3, 12, 10, 0, 0),
            "invalid_schedule_window",
        ),
    ],
)
def test_normalize_schedule_window_rejects_invalid_inputs(
    timezone_name: str,
    start_at: datetime,
    end_at: datetime,
    detail: str,
) -> None:
    """Verify invalid timezone or reversed windows fail with interview-specific reason codes."""
    with pytest.raises(HTTPException) as exc_info:
        normalize_schedule_window(
            scheduled_start_local=start_at,
            scheduled_end_local=end_at,
            timezone_name=timezone_name,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == detail
