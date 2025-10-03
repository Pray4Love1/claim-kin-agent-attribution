"""Utilities for the Codex runner that locates the KinLend f303 vault."""

from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any


def format_withdrawable(value: Any) -> str:
    """Return a human-readable description of a withdrawable balance."""
    if value is None:
        return "Withdrawable: <unknown>"

    try:
        withdrawable_decimal = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return f"Withdrawable: {value}"

    withdrawable_text = format(withdrawable_decimal, "f")
    if "." in withdrawable_text:
        withdrawable_text = withdrawable_text.rstrip("0").rstrip(".")
    if withdrawable_text in {"", "-", "-0"}:
        withdrawable_text = "0"

    return f"Withdrawable: {withdrawable_text}"


__all__ = ["format_withdrawable"]
