"""Codex f303 helpers (Keeper only)."""

from decimal import Decimal, InvalidOperation
from typing import Any, Dict
from hyperliquid.info import Info


DEFAULT_VAULT_ID = "f303"
DEFAULT_OWNER_ADDRESS = "0x996994D2914DF4eEE6176FD5eE152e2922787EE7"


def fetch_leaderboard(info: Info, vault_id: str) -> Dict[str, Any]:
    payload = {"type": "vaultLeaderboard", "vault": vault_id}
    leaderboard = info.post("/info", payload)
    if not isinstance(leaderboard, dict):
        raise TypeError(f"Unexpected leaderboard response type: {type(leaderboard)}")
    return leaderboard


def format_withdrawable(raw_withdrawable: Any) -> str:
    if raw_withdrawable is None:
        return "Withdrawable amount unavailable."
    try:
        withdrawable_decimal = Decimal(str(raw_withdrawable))
    except (InvalidOperation, ValueError):
        return f"Withdrawable (unparsed): {raw_withdrawable}"
    return f"Withdrawable: {withdrawable_decimal.normalize()}"
