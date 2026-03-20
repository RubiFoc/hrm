"""Google Calendar adapter for free-mode shared-calendar interview sync."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

import jwt
from fastapi import HTTPException, status

from hrm_backend.core.errors.http import service_unavailable
from hrm_backend.interviews.models.calendar_binding import InterviewCalendarBinding
from hrm_backend.interviews.models.interview import Interview

GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


@dataclass(frozen=True)
class CalendarBindingSyncPayload:
    """Binding payload returned from calendar sync."""

    interviewer_staff_id: str
    calendar_id: str
    calendar_event_id: str


@dataclass(frozen=True)
class CalendarSyncResult:
    """Result of one schedule sync or cancellation operation."""

    status: str
    bindings: list[CalendarBindingSyncPayload]
    primary_calendar_event_id: str | None = None
    resolved_location_details: str | None = None
    reason_code: str | None = None
    error_detail: str | None = None


class InterviewCalendarAdapter(Protocol):
    """Interface for interview calendar orchestration adapters."""

    def is_configured(self) -> bool:
        """Return whether adapter has runtime credentials and is enabled."""

    def ensure_ready_for_interviewers(self, interviewer_staff_ids: list[str]) -> dict[str, str]:
        """Validate calendar targets for the requested interviewer set."""

    def sync_schedule(
        self,
        *,
        interview: Interview,
        vacancy_title: str,
        candidate_display_name: str,
        existing_bindings: list[InterviewCalendarBinding],
    ) -> CalendarSyncResult:
        """Create or update external events for one interview schedule."""

    def cancel_schedule(
        self,
        *,
        interview: Interview,
        existing_bindings: list[InterviewCalendarBinding],
    ) -> CalendarSyncResult:
        """Delete external events for one cancelled interview."""


class GoogleCalendarAdapter:
    """Service-account Google Calendar adapter for free shared-calendar mode."""

    def __init__(
        self,
        *,
        enabled: bool,
        service_account_key_path: str | None,
        staff_calendar_map: dict[str, str],
    ) -> None:
        """Initialize adapter configuration."""
        self._enabled = enabled
        self._service_account_key_path = (
            None if service_account_key_path is None else service_account_key_path.strip()
        )
        self._staff_calendar_map = {
            key.strip(): value.strip()
            for key, value in staff_calendar_map.items()
            if key.strip() and value.strip()
        }
        self._access_token: str | None = None
        self._access_token_expires_at: float = 0.0

    def is_configured(self) -> bool:
        """Return whether service-account credentials are ready for runtime use."""
        return self._enabled and self._service_account_key_file().is_file()

    def ensure_ready_for_interviewers(self, interviewer_staff_ids: list[str]) -> dict[str, str]:
        """Validate adapter runtime config plus staff-to-calendar mappings."""
        if not self.is_configured():
            raise service_unavailable("calendar_not_configured")

        missing = [
            staff_id
            for staff_id in interviewer_staff_ids
            if staff_id not in self._staff_calendar_map
        ]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="interviewer_calendar_not_configured",
            )

        return {staff_id: self._staff_calendar_map[staff_id] for staff_id in interviewer_staff_ids}

    def sync_schedule(
        self,
        *,
        interview: Interview,
        vacancy_title: str,
        candidate_display_name: str,
        existing_bindings: list[InterviewCalendarBinding],
    ) -> CalendarSyncResult:
        """Create or update shared-calendar events for one interview schedule."""
        calendar_targets = self.ensure_ready_for_interviewers(interview.interviewer_staff_ids_json)
        access_token = self._get_access_token()
        sorted_staff_ids = sorted(interview.interviewer_staff_ids_json)
        binding_map = {item.interviewer_staff_id: item for item in existing_bindings}

        for staff_id in sorted_staff_ids:
            binding = binding_map.get(staff_id)
            conflicting_event_id = self._find_conflicting_event_id(
                access_token=access_token,
                calendar_id=calendar_targets[staff_id],
                interview=interview,
                exclude_event_id=None if binding is None else binding.calendar_event_id,
            )
            if conflicting_event_id is not None:
                return CalendarSyncResult(
                    status="conflict",
                    bindings=[],
                    reason_code="calendar_conflict",
                    error_detail=f"conflicting_event_id={conflicting_event_id}",
                )

        primary_staff_id = sorted_staff_ids[0]
        primary_binding = binding_map.get(primary_staff_id)
        include_conference_data = (
            interview.location_kind == "google_meet" and primary_binding is None
        )
        conference_request_id = (
            f"{interview.interview_id}-{interview.schedule_version}"
            if include_conference_data
            else None
        )
        payload_kwargs = {
            "interview": interview,
            "vacancy_title": vacancy_title,
            "candidate_display_name": candidate_display_name,
            "location_details": interview.location_details,
        }
        primary_payload = self.build_event_payload(
            **payload_kwargs,
            include_conference_data=include_conference_data,
            conference_request_id=conference_request_id,
        )
        try:
            primary_response = self._create_or_update_event(
                access_token=access_token,
                calendar_id=calendar_targets[primary_staff_id],
                current_binding=primary_binding,
                payload=primary_payload,
                include_conference_data=include_conference_data,
            )
        except RuntimeError as exc:
            if not include_conference_data or not self._should_retry_without_conference_data(exc):
                raise
            primary_response = self._create_or_update_event(
                access_token=access_token,
                calendar_id=calendar_targets[primary_staff_id],
                current_binding=primary_binding,
                payload=self.build_event_payload(
                    **payload_kwargs,
                    include_conference_data=False,
                    conference_request_id=None,
                ),
                include_conference_data=False,
            )
        resolved_location_details = (
            self._extract_meet_link(primary_response)
            if interview.location_kind == "google_meet"
            else interview.location_details
        )
        if interview.location_kind == "google_meet" and not resolved_location_details:
            resolved_location_details = interview.location_details

        bindings = [
            CalendarBindingSyncPayload(
                interviewer_staff_id=primary_staff_id,
                calendar_id=calendar_targets[primary_staff_id],
                calendar_event_id=str(primary_response["id"]),
            )
        ]
        for staff_id in sorted_staff_ids[1:]:
            current_binding = binding_map.get(staff_id)
            response = self._create_or_update_event(
                access_token=access_token,
                calendar_id=calendar_targets[staff_id],
                current_binding=current_binding,
                payload=self.build_event_payload(
                    interview=interview,
                    vacancy_title=vacancy_title,
                    candidate_display_name=candidate_display_name,
                    location_details=resolved_location_details,
                    include_conference_data=False,
                    conference_request_id=None,
                ),
                include_conference_data=False,
            )
            bindings.append(
                CalendarBindingSyncPayload(
                    interviewer_staff_id=staff_id,
                    calendar_id=calendar_targets[staff_id],
                    calendar_event_id=str(response["id"]),
                )
            )

        return CalendarSyncResult(
            status="synced",
            bindings=bindings,
            primary_calendar_event_id=str(primary_response["id"]),
            resolved_location_details=resolved_location_details,
        )

    def cancel_schedule(
        self,
        *,
        interview: Interview,
        existing_bindings: list[InterviewCalendarBinding],
    ) -> CalendarSyncResult:
        """Delete previously synchronized shared-calendar events."""
        if not existing_bindings:
            return CalendarSyncResult(status="synced", bindings=[])

        self.ensure_ready_for_interviewers(interview.interviewer_staff_ids_json)
        access_token = self._get_access_token()
        for binding in existing_bindings:
            self._delete_event(
                access_token=access_token,
                calendar_id=binding.calendar_id,
                calendar_event_id=binding.calendar_event_id,
            )
        return CalendarSyncResult(status="synced", bindings=[])

    def build_event_payload(
        self,
        *,
        interview: Interview,
        vacancy_title: str,
        candidate_display_name: str,
        location_details: str | None,
        include_conference_data: bool,
        conference_request_id: str | None,
    ) -> dict[str, object]:
        """Build Google Calendar event payload for one interview."""
        interview_timezone = ZoneInfo(interview.timezone)
        start_value = interview.scheduled_start_at.astimezone(interview_timezone)
        end_value = interview.scheduled_end_at.astimezone(interview_timezone)
        description_lines = [
            f"Vacancy: {vacancy_title}",
            f"Candidate: {candidate_display_name}",
            f"Interview ID: {interview.interview_id}",
            f"Schedule version: {interview.schedule_version}",
        ]
        if location_details:
            description_lines.append(f"Details: {location_details}")

        payload: dict[str, object] = {
            "summary": f"Interview: {vacancy_title}",
            "description": "\n".join(description_lines),
            "start": {
                "dateTime": start_value.isoformat(),
                "timeZone": interview.timezone,
            },
            "end": {
                "dateTime": end_value.isoformat(),
                "timeZone": interview.timezone,
            },
        }
        if location_details:
            payload["location"] = location_details
        if include_conference_data and conference_request_id:
            payload["conferenceData"] = {
                "createRequest": {
                    "requestId": conference_request_id,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
        return payload

    def _service_account_key_file(self) -> Path:
        """Return configured service-account key path."""
        return Path(
            ""
            if self._service_account_key_path is None
            else self._service_account_key_path
        )

    def _get_access_token(self) -> str:
        """Exchange service-account assertion for Calendar API bearer token."""
        if self._access_token and time.time() < self._access_token_expires_at - 30:
            return self._access_token

        credentials = json.loads(self._service_account_key_file().read_text(encoding="utf-8"))
        now = int(time.time())
        assertion = jwt.encode(
            {
                "iss": credentials["client_email"],
                "scope": GOOGLE_CALENDAR_SCOPE,
                "aud": credentials["token_uri"],
                "iat": now,
                "exp": now + 3600,
            },
            credentials["private_key"],
            algorithm="RS256",
        )
        body = urllib.parse.urlencode(
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            }
        ).encode("utf-8")
        response = self._request_json(
            method="POST",
            url=credentials["token_uri"],
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self._access_token = str(response["access_token"])
        self._access_token_expires_at = float(now + int(response.get("expires_in", 3600)))
        return self._access_token

    def _create_or_update_event(
        self,
        *,
        access_token: str,
        calendar_id: str,
        current_binding: InterviewCalendarBinding | None,
        payload: dict[str, object],
        include_conference_data: bool,
    ) -> dict[str, object]:
        """Create or patch one Google Calendar event."""
        encoded_calendar_id = urllib.parse.quote(calendar_id, safe="")
        if current_binding is None:
            query = {"sendUpdates": "none"}
            if include_conference_data:
                query["conferenceDataVersion"] = "1"
            url = (
                f"https://www.googleapis.com/calendar/v3/calendars/{encoded_calendar_id}/events"
                f"?{urllib.parse.urlencode(query)}"
            )
            return self._request_json(
                method="POST",
                url=url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )

        query = {"sendUpdates": "none"}
        if include_conference_data:
            query["conferenceDataVersion"] = "1"
        encoded_event_id = urllib.parse.quote(current_binding.calendar_event_id, safe="")
        url = (
            f"https://www.googleapis.com/calendar/v3/calendars/{encoded_calendar_id}/events/{encoded_event_id}"
            f"?{urllib.parse.urlencode(query)}"
        )
        return self._request_json(
            method="PATCH",
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )

    def _find_conflicting_event_id(
        self,
        *,
        access_token: str,
        calendar_id: str,
        interview: Interview,
        exclude_event_id: str | None,
    ) -> str | None:
        """Return first conflicting event identifier for one calendar if overlap exists."""
        encoded_calendar_id = urllib.parse.quote(calendar_id, safe="")
        query = urllib.parse.urlencode(
            {
                "timeMin": _format_google_timestamp(interview.scheduled_start_at),
                "timeMax": _format_google_timestamp(interview.scheduled_end_at),
                "singleEvents": "true",
                "showDeleted": "false",
                "maxResults": "20",
            }
        )
        url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_calendar_id}/events?{query}"
        response = self._request_json(
            method="GET",
            url=url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        for item in response.get("items", []):
            if not isinstance(item, dict):
                continue
            if item.get("status") == "cancelled":
                continue
            current_event_id = item.get("id")
            if current_event_id and current_event_id == exclude_event_id:
                continue
            if current_event_id:
                return str(current_event_id)
        return None

    def _delete_event(
        self,
        *,
        access_token: str,
        calendar_id: str,
        calendar_event_id: str,
    ) -> None:
        """Delete one Google Calendar event and ignore already-missing rows."""
        encoded_calendar_id = urllib.parse.quote(calendar_id, safe="")
        encoded_event_id = urllib.parse.quote(calendar_event_id, safe="")
        url = (
            f"https://www.googleapis.com/calendar/v3/calendars/{encoded_calendar_id}/events/{encoded_event_id}"
            "?sendUpdates=none"
        )
        try:
            self._request_json(
                method="DELETE",
                url=url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except RuntimeError as exc:
            if "404" in str(exc):
                return
            raise

    def _request_json(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        data: bytes | None = None,
    ) -> dict[str, object]:
        """Perform one Google API request and decode JSON response when present."""
        request = urllib.request.Request(url=url, method=method, headers=headers, data=data)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                raw_body = response.read().decode("utf-8")
                if not raw_body.strip():
                    return {}
                return json.loads(raw_body)
        except urllib.error.HTTPError as exc:
            raw_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Google Calendar request failed with status {exc.code}: {raw_body[:512]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Google Calendar request failed: {exc.reason}") from exc

    @staticmethod
    def _should_retry_without_conference_data(exc: RuntimeError) -> bool:
        """Return whether Meet conference creation should retry without conferenceData."""
        message = str(exc).lower()
        return "invalid conference type value" in message or "conference type value" in message

    @staticmethod
    def _extract_meet_link(payload: dict[str, object]) -> str | None:
        """Extract Google Meet link from event response payload when present."""
        hangout_link = payload.get("hangoutLink")
        if isinstance(hangout_link, str) and hangout_link.strip():
            return hangout_link.strip()
        conference_data = payload.get("conferenceData")
        if not isinstance(conference_data, dict):
            return None
        entry_points = conference_data.get("entryPoints")
        if not isinstance(entry_points, list):
            return None
        for item in entry_points:
            if not isinstance(item, dict):
                continue
            uri = item.get("uri")
            if isinstance(uri, str) and uri.strip():
                return uri.strip()
        return None


def _format_google_timestamp(value: datetime) -> str:
    """Format UTC-aware datetime into Google API timestamp."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
