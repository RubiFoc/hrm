"""Unit tests for referral normalization helpers."""

from __future__ import annotations

from hrm_backend.referrals.utils.referral_utils import (
    normalize_email,
    normalize_full_name,
    normalize_phone,
    split_full_name,
)


def test_normalize_email_trims_and_lowercases() -> None:
    """Verify email normalization strips whitespace and lowercases."""
    assert normalize_email(" Alice@Example.COM ") == "alice@example.com"


def test_normalize_phone_trims_only() -> None:
    """Verify phone normalization trims whitespace without changing content."""
    assert normalize_phone(" +375291112233 ") == "+375291112233"


def test_normalize_full_name_collapses_whitespace() -> None:
    """Verify full name normalization collapses extra whitespace."""
    assert normalize_full_name("  Alice   B.  Doe ") == "Alice B. Doe"


def test_split_full_name_single_part_dupes_into_last_name() -> None:
    """Verify single-part name maps to both first and last name."""
    first, last = split_full_name("Cher")
    assert first == "Cher"
    assert last == "Cher"


def test_split_full_name_multiple_parts_keeps_tail() -> None:
    """Verify multi-part name keeps remaining parts as last name."""
    first, last = split_full_name("Ada Lovelace Byron")
    assert first == "Ada"
    assert last == "Lovelace Byron"
