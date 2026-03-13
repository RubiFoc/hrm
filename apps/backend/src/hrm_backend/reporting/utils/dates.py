"""Helpers for KPI snapshot monthly date windows."""

from __future__ import annotations

from datetime import UTC, date, datetime, time


def month_bounds(period_month: date) -> tuple[datetime, datetime]:
    """Return UTC datetime bounds for the provided month.

    Args:
        period_month: First day of the month.

    Returns:
        tuple[datetime, datetime]: Inclusive start and exclusive end timestamps in UTC.
    """
    start = datetime.combine(period_month, time.min, tzinfo=UTC)
    if period_month.month == 12:
        next_month = date(period_month.year + 1, 1, 1)
    else:
        next_month = date(period_month.year, period_month.month + 1, 1)
    end = datetime.combine(next_month, time.min, tzinfo=UTC)
    return start, end


def ensure_month_start(period_month: date) -> date:
    """Validate that the provided date is the first day of a month.

    Args:
        period_month: Date to validate.

    Returns:
        date: The same date when valid.

    Raises:
        ValueError: When the date is not the first day of the month.
    """
    if period_month.day != 1:
        raise ValueError("period_month must be the first day of the month")
    return period_month
