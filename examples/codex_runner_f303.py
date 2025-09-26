"""Utility helpers for Codex runner output formatting."""

from __future__ import annotations

from decimal import Decimal


def format_withdrawable(withdrawable: str) -> str:
    """Format withdrawable amounts without scientific notation.

    The API occasionally returns withdrawable balances in decimal strings
    that represent whole numbers (for example ``"1000"`` or ``"1000.0"``).
    ``Decimal.normalize`` would emit those values in scientific notation,
    e.g. ``Decimal("1000").normalize()`` -> ``Decimal("1E+3")`` which is
    harder to read in CLI output.  Format as a fixed-point decimal, trimming
    only insignificant trailing zeros so whole-number results remain
    human-readable.
    """

    withdrawable_decimal = Decimal(withdrawable)

    if withdrawable_decimal.is_zero():
        fixed_point = "0"
    else:
        fixed_point = format(withdrawable_decimal, "f")
        if "." in fixed_point:
            fixed_point = fixed_point.rstrip("0").rstrip(".")

    return f"Withdrawable: {fixed_point}"


__all__ = ["format_withdrawable"]
