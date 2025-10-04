#!/usr/bin/env python3
"""Trigger a Hyperliquid withdrawal using the configured Codex API wallet."""
from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal
from typing import Sequence

from claim_kin_agent_attribution.withdrawals import (
    DEFAULT_DESTINATION,
    load_api_wallet,
    perform_withdrawal,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Submit a withdraw-from-bridge action using the Codex API wallet.",
    )
    parser.add_argument("--amount", required=True, help="Amount of USD to withdraw (e.g. 1000000)")
    parser.add_argument(
        "--destination",
        default=os.getenv("CODEX_DEFAULT_DESTINATION", DEFAULT_DESTINATION),
        help="Destination wallet address. Defaults to the Codex treasury address.",
    )
    parser.add_argument(
        "--account",
        default=None,
        help=(
            "Override the Hyperliquid account to withdraw from. When omitted the "
            "account configured for the API wallet is used."
        ),
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("HL_API_URL"),
        help="Override the Hyperliquid API base URL (falls back to mainnet when unset).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the API response as JSON for downstream scripting.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        amount = Decimal(args.amount)
    except Exception as error:  # pragma: no cover - argparse already validates basics
        parser.error(f"Invalid --amount value: {error}")
        return 2

    wallet, configured_account = load_api_wallet()
    effective_account = args.account or configured_account
    response = perform_withdrawal(
        amount,
        args.destination,
        wallet,
        base_url=args.base_url,
        account_address=effective_account,
    )

    if args.json:
        json.dump(response, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        formatted_amount = f"{amount:,.2f}"
        print(
            f"Submitted withdrawal of ${formatted_amount} USD from {effective_account} to {args.destination}.",
        )
        print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

