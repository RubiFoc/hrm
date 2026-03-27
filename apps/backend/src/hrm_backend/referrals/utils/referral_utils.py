"""Helpers for normalizing referral payload fields."""

from __future__ import annotations


def normalize_email(value: str) -> str:
    """Normalize referral email string.

    Args:
        value: Raw email string.

    Returns:
        str: Lowercased, trimmed email.
    """
    return value.strip().lower()


def normalize_phone(value: str) -> str:
    """Normalize referral phone string.

    Args:
        value: Raw phone string.

    Returns:
        str: Trimmed phone string.
    """
    return value.strip()


def normalize_full_name(value: str) -> str:
    """Normalize full name input into a single-space string.

    Args:
        value: Raw full-name input.

    Returns:
        str: Normalized full name.
    """
    return " ".join(value.strip().split())


def split_full_name(value: str) -> tuple[str, str]:
    """Split normalized full name into first/last name parts.

    Args:
        value: Normalized full-name input.

    Returns:
        tuple[str, str]: First name and last name pair.
    """
    parts = [part for part in value.split(" ") if part]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[0], " ".join(parts[1:])
