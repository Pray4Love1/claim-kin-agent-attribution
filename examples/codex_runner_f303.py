"""Codex helper for inspecting the KinLend vault f303 leaderboard."""

from __future__ import annotations

import argparse
from pprint import pprint

from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.f303_helpers import (
    DEFAULT_OWNER_ADDRESS,
    DEFAULT_VAULT_ID,
    fetch_leaderboard,
)
from examples.format_utils import format_withdrawable  # ✅ updated


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


def main() -> None:
    args = parse_args()
    info = Info(args.base_url, skip_ws=True)

    print(f"Requesting leaderboard for vault '{args.vault_id}' at {args.base_url}...")
    leaderboard = fetch_leaderboard(info, args.vault_id)
    pprint(leaderboard)

    print(f"\nFetching clearinghouse state for owner {args.owner_address}...")
    clearinghouse_state = info.user_state(args.owner_address)
    if not isinstance(clearinghouse_state, dict):
        print("Unexpected clearinghouse state type:", type(clearinghouse_state).__name__)
        return

    withdrawable_message = format_withdrawable(clearinghouse_state.get("withdrawable"))
    print(withdrawable_message)


if __name__ == "__main__":
    main()
