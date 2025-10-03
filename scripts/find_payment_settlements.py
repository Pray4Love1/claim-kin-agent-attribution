#!/usr/bin/env python3
"""Fetch and summarise USD payment settlements for a Hyperliquid account."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Sequence

from hyperliquid.info import Info

from claim_kin_agent_attribution.payments import (
    PaymentSettlement,
    extract_payment_settlements,
    total_settlement_amount,
)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Retrieve Hyperliquid ledger updates for an address and display the USD "
            "payment settlements that affect account balances."
        )
    )
    parser.add_argument("address", help="Hyperliquid on-chain address (0x...) to inspect.")
    parser.add_argument(
        "--start",
        type=int,
        required=True,
        help="Start timestamp in milliseconds since epoch for ledger lookups.",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="Optional end timestamp in milliseconds since epoch.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a formatted table."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit output to the most recent N settlements after sorting by time.",
    )
    return parser


def _format_amount(amount: Decimal) -> str:
    quantised = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantised:,.2f}"


def _format_settlement(settlement: PaymentSettlement) -> str:
    timestamp = settlement.timestamp.astimezone(timezone.utc).isoformat()
    direction = settlement.direction.upper()
    amount = _format_amount(settlement.amount_usd)
    return (
        f"{timestamp} | {direction:5} | {amount} USD | {settlement.kind} | "
        f"{settlement.tx_hash}"
    )


def _maybe_limit(settlements: Sequence[PaymentSettlement], limit: int | None) -> Iterable[PaymentSettlement]:
    if limit is None or limit <= 0 or limit >= len(settlements):
        return settlements
    return settlements[-limit:]


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(argv)

    info = Info(skip_ws=True)
    updates = info.user_non_funding_ledger_updates(
        user=args.address,
        startTime=args.start,
        endTime=args.end,
    )
    settlements = extract_payment_settlements(updates)

    limited = list(_maybe_limit(settlements, args.limit))

    if args.json:
        payload = [settlement.as_dict() for settlement in limited]
        json.dump(
            {
                "address": args.address,
                "start": args.start,
                "end": args.end,
                "net_usd": str(total_settlement_amount(limited)),
                "settlements": payload,
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0

    if not limited:
        print("No payment settlements found for the requested window.")
        return 0

    print("UTC Timestamp | DIR   | Amount (USD) | Type | Transaction Hash")
    print("-" * 86)
    for settlement in limited:
        print(_format_settlement(settlement))

    net = total_settlement_amount(limited)
    print("-" * 86)
    print(f"Net change across listed settlements: {_format_amount(net)} USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
