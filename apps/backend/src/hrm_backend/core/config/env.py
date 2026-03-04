"""Environment variable helper functions shared across backend domains."""

from __future__ import annotations


def read_positive_int_env(raw_value: str | None, default: int) -> int:
    """Parse a positive integer from env-like input with default fallback.

    Args:
        raw_value: Raw string value (typically from environment variables).
        default: Fallback value used for missing or invalid inputs.

    Returns:
        int: Parsed positive integer or fallback value.
    """
    if raw_value is None:
        return default

    try:
        parsed = int(raw_value)
    except ValueError:
        return default

    return parsed if parsed > 0 else default


def normalize_non_empty(raw_value: str | None, fallback: str) -> str:
    """Normalize string input to a non-empty value.

    Args:
        raw_value: Raw string input, potentially empty or `None`.
        fallback: Fallback used when normalized value is empty.

    Returns:
        str: Non-empty normalized string.
    """
    candidate = "" if raw_value is None else raw_value.strip()
    return candidate if candidate else fallback
