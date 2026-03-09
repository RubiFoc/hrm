"""Schedule validation and normalization helpers for interviews."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status


def normalize_schedule_window(
    *,
    scheduled_start_local: datetime,
    scheduled_end_local: datetime,
    timezone_name: str,
) -> tuple[datetime, datetime, str]:
    """Validate local schedule inputs and convert them to UTC storage timestamps."""
    normalized_timezone = timezone_name.strip()
    if not normalized_timezone:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_timezone",
        )

    if scheduled_start_local.tzinfo is not None or scheduled_end_local.tzinfo is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_schedule_window",
        )

    try:
        zone = ZoneInfo(normalized_timezone)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_timezone",
        ) from exc

    start_at = scheduled_start_local.replace(tzinfo=zone).astimezone(UTC)
    end_at = scheduled_end_local.replace(tzinfo=zone).astimezone(UTC)
    if end_at <= start_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_schedule_window",
        )
    return start_at, end_at, normalized_timezone
