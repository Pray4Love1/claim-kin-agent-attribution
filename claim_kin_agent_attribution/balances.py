"""Utilities for summarising Hyperliquid account balances."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping


def extract_withdrawable_balance(user_state: Mapping[str, Any]) -> Decimal:
    """Return the withdrawable USD balance from a user state payload.

    Args:
        user_state: Mapping returned by :meth:`hyperliquid.info.Info.user_state`.

    Returns:
        The withdrawable amount expressed as a :class:`~decimal.Decimal`.

    Raises:
        ValueError: If the payload does not include a withdrawable value.
    """

    try:
        withdrawable = user_state["clearinghouseState"]["withdrawable"]
    except KeyError as exc:  # pragma: no cover - exercised in tests
        raise ValueError("User state payload missing withdrawable balance") from exc

    if withdrawable in (None, ""):
        raise ValueError("Withdrawable balance is empty in payload")

    return Decimal(str(withdrawable))
