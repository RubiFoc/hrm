"""Time helper functions reused by multiple backend packages."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now_epoch() -> int:
    """Return current UTC timestamp in seconds.

    Returns:
        int: Current UNIX timestamp in UTC.
    """
    return int(datetime.now(tz=UTC).timestamp())


def ttl_until_epoch(target_epoch: int, now_epoch: int | None = None) -> int:
    """Calculate non-negative TTL from target UNIX timestamp.

    Args:
        target_epoch: Target UNIX timestamp.
        now_epoch: Optional current UNIX timestamp override.

    Returns:
        int: Number of seconds until `target_epoch`, never negative.
    """
    current = utc_now_epoch() if now_epoch is None else now_epoch
    return max(0, target_epoch - current)
