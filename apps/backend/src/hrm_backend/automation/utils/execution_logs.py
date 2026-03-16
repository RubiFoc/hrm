"""Helpers for automation execution log hygiene.

This module provides:
- UTC normalization helpers for timestamps stored in execution logs,
- minimal PII-safe sanitization for error strings recorded in durable logs.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

_EMAIL_PATTERN = re.compile(
    r"(?P<email>[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
    re.IGNORECASE,
)
_PHONE_PATTERN = re.compile(r"(?P<phone>\+?\d[\d\s().-]{6,}\d)")


def normalize_datetime_utc(value: datetime) -> datetime:
    """Normalize datetime to timezone-aware UTC.

    Args:
        value: Input datetime value (naive or timezone-aware).

    Returns:
        datetime: Timezone-aware UTC datetime.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def sanitize_error_text(raw: str, *, max_length: int = 512) -> str:
    """Sanitize and truncate an error string for durable non-PII logs.

    The goal is to avoid accidental persistence of emails/phones and to keep the stored payload
    bounded. This does not attempt full PII classification; execution logs still must not include
    user-controlled free-form content.

    Args:
        raw: Raw error string (typically `str(exc)`).
        max_length: Maximum length of the resulting string.

    Returns:
        str: Sanitized, single-line, truncated error string.
    """
    normalized = " ".join(raw.split())
    redacted = _EMAIL_PATTERN.sub("<redacted_email>", normalized)
    redacted = _PHONE_PATTERN.sub("<redacted_phone>", redacted)
    return redacted[:max_length]

