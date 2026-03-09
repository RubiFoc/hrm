"""Unit tests for Google Calendar interview adapter mapping and validation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import HTTPException

from hrm_backend.interviews.infra.google_calendar.adapter import (
    CalendarBindingSyncPayload,
    CalendarSyncResult,
    GoogleCalendarAdapter,
)
from hrm_backend.interviews.models.calendar_binding import InterviewCalendarBinding
from hrm_backend.interviews.models.interview import Interview


def _write_key_file(tmp_path: Path) -> str:
    key_path = tmp_path / "service-account.json"
    key_path.write_text(json.dumps({"client_email": "svc@example.com"}), encoding="utf-8")
    return str(key_path)


def _build_interview(*, interviewer_staff_ids: list[str] | None = None) -> Interview:
    return Interview(
        interview_id="interview-1",
        vacancy_id="vacancy-1",
        candidate_id="candidate-1",
        status="pending_sync",
        calendar_sync_status="queued",
        schedule_version=2,
        scheduled_start_at=datetime(2026, 3, 12, 7, 0, 0, tzinfo=UTC),
        scheduled_end_at=datetime(2026, 3, 12, 8, 0, 0, tzinfo=UTC),
        timezone="Europe/Minsk",
        location_kind="google_meet",
        location_details=None,
        interviewer_staff_ids_json=interviewer_staff_ids or ["staff-a", "staff-b"],
        candidate_response_status="pending",
        created_by_staff_id="staff-owner",
        updated_by_staff_id="staff-owner",
    )


def test_google_calendar_adapter_requires_runtime_configuration(tmp_path: Path) -> None:
    """Verify adapter refuses sync when feature flag or key file is missing."""
    disabled = GoogleCalendarAdapter(
        enabled=False,
        service_account_key_path=_write_key_file(tmp_path),
        staff_calendar_map={"staff-a": "alpha@example.com"},
    )
    missing_key = GoogleCalendarAdapter(
        enabled=True,
        service_account_key_path=str(tmp_path / "missing.json"),
        staff_calendar_map={"staff-a": "alpha@example.com"},
    )

    for adapter in (disabled, missing_key):
        with pytest.raises(HTTPException) as exc_info:
            adapter.ensure_ready_for_interviewers(["staff-a"])

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "calendar_not_configured"


def test_google_calendar_adapter_requires_calendar_mapping_for_each_interviewer(
    tmp_path: Path,
) -> None:
    """Verify missing staff-calendar mapping fails with the planned 422 reason code."""
    adapter = GoogleCalendarAdapter(
        enabled=True,
        service_account_key_path=_write_key_file(tmp_path),
        staff_calendar_map={"staff-a": "alpha@example.com"},
    )

    with pytest.raises(HTTPException) as exc_info:
        adapter.ensure_ready_for_interviewers(["staff-a", "staff-b"])

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "interviewer_calendar_not_configured"


def test_google_calendar_adapter_builds_meet_event_payload() -> None:
    """Verify Meet event payload contains timezone-aware schedule data and conference request."""
    adapter = GoogleCalendarAdapter(
        enabled=True,
        service_account_key_path="/tmp/not-used.json",
        staff_calendar_map={},
    )

    payload = adapter.build_event_payload(
        interview=_build_interview(),
        vacancy_title="Backend Engineer",
        candidate_display_name="Jane Doe",
        location_details=None,
        include_conference_data=True,
        conference_request_id="req-1",
    )

    assert payload["summary"] == "Interview: Backend Engineer"
    assert payload["start"] == {
        "dateTime": "2026-03-12T10:00:00+03:00",
        "timeZone": "Europe/Minsk",
    }
    assert payload["end"] == {
        "dateTime": "2026-03-12T11:00:00+03:00",
        "timeZone": "Europe/Minsk",
    }
    assert payload["conferenceData"] == {
        "createRequest": {
            "requestId": "req-1",
            "conferenceSolutionKey": {"type": "hangoutsMeet"},
        }
    }


def test_google_calendar_adapter_syncs_primary_meet_then_secondary_shared_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify primary interviewer gets Meet creation and secondaries reuse resolved link."""
    adapter = GoogleCalendarAdapter(
        enabled=True,
        service_account_key_path=_write_key_file(tmp_path),
        staff_calendar_map={
            "staff-a": "alpha@example.com",
            "staff-b": "beta@example.com",
        },
    )
    created_calls: list[dict[str, object]] = []

    monkeypatch.setattr(adapter, "_get_access_token", lambda: "token")
    monkeypatch.setattr(adapter, "_find_conflicting_event_id", lambda **_: None)

    def _create_or_update_event(**kwargs: object) -> dict[str, object]:
        created_calls.append(kwargs)
        if kwargs["calendar_id"] == "alpha@example.com":
            return {
                "id": "evt-alpha",
                "hangoutLink": "https://meet.google.com/alpha-room",
            }
        return {"id": "evt-beta"}

    monkeypatch.setattr(adapter, "_create_or_update_event", _create_or_update_event)

    result = adapter.sync_schedule(
        interview=_build_interview(),
        vacancy_title="Backend Engineer",
        candidate_display_name="Jane Doe",
        existing_bindings=[],
    )

    assert result == CalendarSyncResult(
        status="synced",
        bindings=[
            CalendarBindingSyncPayload(
                interviewer_staff_id="staff-a",
                calendar_id="alpha@example.com",
                calendar_event_id="evt-alpha",
            ),
            CalendarBindingSyncPayload(
                interviewer_staff_id="staff-b",
                calendar_id="beta@example.com",
                calendar_event_id="evt-beta",
            ),
        ],
        primary_calendar_event_id="evt-alpha",
        resolved_location_details="https://meet.google.com/alpha-room",
    )
    assert created_calls[0]["include_conference_data"] is True
    assert created_calls[1]["include_conference_data"] is False
    assert created_calls[1]["payload"]["location"] == "https://meet.google.com/alpha-room"


def test_google_calendar_adapter_detects_conflicts_before_writing_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify overlapping events short-circuit into deterministic conflict status."""
    adapter = GoogleCalendarAdapter(
        enabled=True,
        service_account_key_path=_write_key_file(tmp_path),
        staff_calendar_map={"staff-a": "alpha@example.com"},
    )
    monkeypatch.setattr(adapter, "_get_access_token", lambda: "token")
    monkeypatch.setattr(adapter, "_find_conflicting_event_id", lambda **_: "busy-event")

    result = adapter.sync_schedule(
        interview=_build_interview(interviewer_staff_ids=["staff-a"]),
        vacancy_title="Backend Engineer",
        candidate_display_name="Jane Doe",
        existing_bindings=[
            InterviewCalendarBinding(
                interview_id="interview-1",
                interviewer_staff_id="staff-a",
                calendar_id="alpha@example.com",
                calendar_event_id="evt-alpha",
                schedule_version=1,
            )
        ],
    )

    assert result.status == "conflict"
    assert result.reason_code == "calendar_conflict"
    assert "busy-event" in (result.error_detail or "")
