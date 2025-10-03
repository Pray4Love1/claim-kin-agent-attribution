"""Utility helpers for KinLend vault f303 runner output formatting."""

from __future__ import annotations
from decimal import Decimal


def format_withdrawable(withdrawable: str | None) -> str:
    """Format withdrawable amounts without scientific notation.

    Ensures whole numbers remain human-readable while trimming
    insignificant trailing zeros.
    """
    if withdrawable is None:
        return "Withdrawable: N/A"

    withdrawable_decimal = Decimal(withdrawable)

    if withdrawable_decimal.is_zero():
        fixed_point = "0"
    else:
        fixed_point = format(withdrawable_decimal, "f")
        if "." in fixed_point:
            fixed_point = fixed_point.rstrip("0").rstrip(".")

    return f"Withdrawable: {fixed_point}"


DEFAULT_OWNER_ADDRESS = "0xKinLendVaultOwner"   # TODO: update if controller changes
DEFAULT_VAULT_ID = "f303"


__all__ = [
    "format_withdrawable",
    "DEFAULT_OWNER_ADDRESS",
    "DEFAULT_VAULT_ID",
]
