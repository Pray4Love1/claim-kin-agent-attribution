#!/usr/bin/env python3
"""Codex helper for inspecting the KinLend vault f303 leaderboard.

This script is bound to your vault/controller and not reusable by others.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from pprint import pprint
from typing import Any, Dict

from hyperliquid.info import Info
from hyperliquid.utils import constants

DEFAULT_VAULT_ID = "f303"
DEFAULT_OWNER_ADDRESS = "0x996994D2914DF4eEE6176FD5eE152e2922787EE7"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch the KinLend vault leaderboard entry and withdrawable state."
    )
    parser.add_argument("--vault-id", default=DEFAULT_VAULT_ID)
    parser.add_argument("--owner-address", default=DEFAULT_OWNER_ADDRESS)
    parser.add_argument("--base-url", default=constants.MAINNET_API_URL)
    return parser.parse_args()


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


def main() -> None:
    args = parse_args()
    info = Info(args.base_url, skip_ws=True)
    leaderboard = fetch_leaderboard(info, args.vault_id)
    pprint(leaderboard)
    clearinghouse_state = info.user_state(args.owner_address)
    withdrawable_message = format_withdrawable(clearinghouse_state.get("withdrawable"))
    print(withdrawable_message)


if __name__ == "__main__":
    main()
