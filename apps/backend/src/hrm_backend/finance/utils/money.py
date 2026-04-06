"""Shared money normalization utilities for compensation controls."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CURRENCY_CODE = "BYN"
MONEY_QUANTIZE = Decimal("0.01")


def normalize_amount(value: float) -> float:
    """Round a numeric amount to the fixed money precision.

    Args:
        value: Raw numeric amount.

    Returns:
        float: Amount rounded to two decimal places using half-up rounding.
    """
    quantized = Decimal(str(value)).quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP)
    return float(quantized)


def normalize_currency(currency: str | None = None) -> str:
    """Return the canonical currency code or raise on mismatched value.

    Args:
        currency: Optional input currency to validate.

    Returns:
        str: Canonical currency code.

    Raises:
        ValueError: When the provided currency is not supported.
    """
    if currency is None or currency == CURRENCY_CODE:
        return CURRENCY_CODE
    raise ValueError("Unsupported currency: only BYN is allowed")
