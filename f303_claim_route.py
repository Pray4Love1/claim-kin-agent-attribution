#!/usr/bin/env python3
"""Inspect the KinLend f303 vault claim route with a local wallet."""

from __future__ import annotations

import argparse
import os
from pprint import pprint
from typing import Optional

from eth_account import Account

from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.f303_helpers import (
    DEFAULT_OWNER_ADDRESS,
    DEFAULT_VAULT_ID,
    fetch_leaderboard,
    format_withdrawable,
)


def derive_owner_from_env() -> Optional[str]:
    """Return the wallet address derived from ``PRIVATE_KEY`` if available."""
    private_key = os.environ.get("PRIVATE_KEY")
    if not private_key:
        return None

    try:
        return Account.from_key(private_key).address
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise SystemExit(f"Failed to load account from PRIVATE_KEY: {exc}") from exc


def parse_args(env_owner: Optional[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Query the KinLend f303 leaderboard and clearinghouse withdrawable value "
            "used in the attribution claim."
        )
    )
    parser.add_argument(
        "--vault-id",
        default=DEFAULT_VAULT_ID,
        help="Hyperliquid vault identifier to query (default: %(default)s)",
    )
    parser.add_argument(
        "--base-url",
        default=constants.MAINNET_API_URL,
        help="Hyperliquid API base URL (defaults to mainnet).",
    )
    parser.add_argument(
        "--owner-address",
        default=env_owner or DEFAULT_OWNER_ADDRESS,
        help=(
            "Vault owner address used when requesting the clearinghouse state. "
            "Defaults to the PRIVATE_KEY-derived wallet if present."
        ),
    )
    return parser.parse_args()


def main() -> None:
    derived_owner = derive_owner_from_env()
    args = parse_args(derived_owner)

    info = Info(args.base_url, skip_ws=True)

    if derived_owner:
        print(f"🔐 Derived owner address from PRIVATE_KEY: {derived_owner}")
        if args.owner_address.lower() != derived_owner.lower():
            print(
                "⚠️ --owner-address overrides the PRIVATE_KEY-derived wallet. "
                "Ensure this matches the active vault controller."
            )
    else:
        print(
            "⚠️ PRIVATE_KEY not set; falling back to the configured owner address. "
            "Pass --owner-address explicitly if the vault controller has rotated."
        )

    print(f"\nRequesting leaderboard for vault '{args.vault_id}' at {args.base_url}...")
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

    print("\n📄 Reference: claims/f303_attribution.json")


if __name__ == "__main__":
    main()
