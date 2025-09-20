"""Utilities for inspecting the KinLend f303 vault state."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from hyperliquid.info import Info

DEFAULT_VAULT_ID = "f303"
DEFAULT_OWNER_ADDRESS = "0x996994D2914DF4eEE6176FD5eE152e2922787EE7"


def fetch_leaderboard(info: "Info", vault_id: str) -> Dict[str, Any]:
    """Return the leaderboard payload for a vault."""
    payload = {"type": "vaultLeaderboard", "vault": vault_id}
    leaderboard = info.post("/info", payload)
    if not isinstance(leaderboard, dict):
        raise TypeError(f"Unexpected leaderboard response type: {type(leaderboard)!r}")
    return leaderboard


def format_withdrawable(raw_withdrawable: Any) -> str:
    """Render the clearinghouse withdrawable balance for human readers."""
    if raw_withdrawable is None:
        return "Withdrawable amount unavailable in clearinghouse response."

    try:
        withdrawable_decimal = Decimal(str(raw_withdrawable))
    except (InvalidOperation, ValueError):
        return f"Withdrawable (unparsed): {raw_withdrawable}"

    withdrawable_str = format(withdrawable_decimal, "f")
    if "." in withdrawable_str:
        withdrawable_str = withdrawable_str.rstrip("0").rstrip(".")
    return f"Withdrawable: {withdrawable_str}"
