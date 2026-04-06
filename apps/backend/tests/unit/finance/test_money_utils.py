"""Unit tests for compensation money utilities."""

from __future__ import annotations

import pytest

from hrm_backend.finance.utils.money import CURRENCY_CODE, normalize_amount, normalize_currency


def test_normalize_amount_rounds_to_two_decimals() -> None:
    """Verify money normalization uses two-decimal precision."""
    assert normalize_amount(1500.555) == 1500.56
    assert normalize_amount(1500.554) == 1500.55


def test_normalize_currency_accepts_only_byn() -> None:
    """Verify unsupported currency values are rejected."""
    assert normalize_currency() == CURRENCY_CODE
    assert normalize_currency(CURRENCY_CODE) == CURRENCY_CODE
    with pytest.raises(ValueError):
        normalize_currency("USD")
