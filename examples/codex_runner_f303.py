"""Codex helper for inspecting the KinLend vault f303 leaderboard."""

from __future__ import annotations
from decimal import Decimal
import argparse
from pprint import pprint

from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.f303_helpers import (
    DEFAULT_OWNER_ADDRESS,
    DEFAULT_VAULT_ID,
    fetch_leaderboard,
)
from examples.format_utils import format_withdrawable  # ✅ already updated

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


DEFAULT_OWNER_ADDRESS = "0xKinLendVaultOwner"   # ✅ Update this if controller changes
DEFAULT_VAULT_ID = "f303"

__all__ = [
    "format_withdrawable",
    "DEFAULT_OWNER_ADDRESS",
    "DEFAULT_VAULT_ID",
]
