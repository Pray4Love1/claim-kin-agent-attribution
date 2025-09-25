"""Codex helper for inspecting the KinLend vault f303 leaderboard.

Run this script to print the Hyperliquid vault leaderboard response and the
clearinghouse withdrawable balance for the vault owner. Supply the vault owner
address at runtime so the withdrawable figure reflects the wallet that actually
receives vault fees:

    python examples/codex_runner_f303.py --owner-address 0xYourVaultOwner

If you omit ``--owner-address`` the script defaults to the KinLend owner used in
Keeper attestations. Update the default below if the vault migrates to a new
controller.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from pprint import pprint
from typing import Any, Dict

from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.f303_helpers import (
    DEFAULT_OWNER_ADDRESS,
    DEFAULT_VAULT_ID,
    fetch_leaderboard,
    format_withdrawable,
)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch the KinLend vault leaderboard entry and withdrawable state."
    )
    parser.add_argument(
        "--vault-id",
        default=DEFAULT_VAULT_ID,
        help="Hyperliquid vault identifier to query (default: %(default)s)",
    )
    parser.add_argument(
        "--owner-address",
        default=DEFAULT_OWNER_ADDRESS,
        help="Vault owner address used for clearinghouse withdrawable lookup.",
    )
    parser.add_argument(
        "--base-url",
        default=constants.MAINNET_API_URL,
        help="Hyperliquid API base URL (defaults to mainnet).",
    )
    return parser.parse_args()

def fetch_leaderboard(info: Info, vault_id: str) -> Dict[str, Any]:
    """Return the leaderboard payload for a vault."""
    payload = {"type": "vaultLeaderboard", "vault": vault_id}
    leaderboard = info.post("/info", payload)
    if not isinstance(leaderboard, dict):
        raise TypeError("Unexpected leaderboard response type: %r" % type(leaderboard))
    return leaderboard

def format_withdrawable(raw_withdrawable: Any) -> str:
    if raw_withdrawable is None:
        return "Withdrawable amount unavailable in clearinghouse response."
    try:
        withdrawable_decimal = Decimal(str(raw_withdrawable))
    except (InvalidOperation, ValueError):
        return f"Withdrawable (unparsed): {raw_withdrawable}"
    return f"Withdrawable: {withdrawable_decimal.normalize()}"

def main() -> None:
    args = parse_args()
    info = Info(args.base_url, skip_ws=True)

    print(f"Requesting leaderboard for vault '{args.vault_id}' at {args.base_url}...")
    leaderboard = fetch_leaderboard(info, args.vault_id)
    pprint(leaderboard)

    print(f"\nFetching clearinghouse state for owner {args.owner_address}...")
    clearinghouse_state = info.user_state(args.owner_address)
    if not isinstance(clearinghouse_state, dict):
        print(
            "Unexpected clearinghouse state type:",
            type(clearinghouse_state).__name__,
        )
        return

    withdrawable_message = format_withdrawable(clearinghouse_state.get("withdrawable"))
    print(withdrawable_message)


if __name__ == "__main__":
    main()
