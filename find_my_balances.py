#!/usr/bin/env python3
"""Utility for fetching Hyperliquid perp and spot balances for an address."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Optional

try:
    from requests import RequestException
except Exception:  # pragma: no cover - requests may not be available in some environments
    RequestException = Exception  # type: ignore[assignment]

from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.error import ClientError, ServerError


def _format_number(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return ("{:.8f}".format(value)).rstrip("0").rstrip(".") or "0"


def _print_perp(perp: Dict[str, Any]) -> None:
    print("Perp account:")
    account_value = _format_number(perp.get("accountValue"))
    withdrawable = _format_number(perp.get("withdrawable"))
    print(f"  Account value: {account_value}")
    print(f"  Withdrawable: {withdrawable}")

    positions = perp.get("positions", [])
    if not positions:
        print("  No open perp positions.")
        return

    print("  Positions:")
    for position in positions:
        coin = position.get("coin", "?")
        size = _format_number(position.get("size"))
        position_value = _format_number(position.get("positionValue"))
        unrealized = _format_number(position.get("unrealizedPnl"))
        margin_used = _format_number(position.get("marginUsed"))
        print(
            f"    - {coin}: size={size}, positionValue={position_value}, "
            f"unrealizedPnL={unrealized}, marginUsed={margin_used}"
        )


def _print_spot(spot: Dict[str, Any]) -> None:
    print("Spot balances:")
    balances = spot.get("balances", [])
    if not balances:
        print("  No spot balances.")
        return

    for balance in balances:
        token_name = balance.get("tokenName") or balance.get("token") or "?"
        total = _format_number(balance.get("total"))
        available = _format_number(balance.get("available"))
        usd_value = balance.get("usdValue")
        usd_value_str = _format_number(usd_value)
        extra = f", usdValue={usd_value_str}" if usd_value is not None else ""
        print(f"  - {token_name}: total={total}, available={available}{extra}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address", help="Onchain address (0x...) to inspect")
    parser.add_argument(
        "--base-url",
        default=constants.MAINNET_API_URL,
        help="Hyperliquid API base URL (defaults to mainnet)",
    )
    parser.add_argument(
        "--include-zero",
        action="store_true",
        help="Include zero balances and flat positions in the output",
    )
    parser.add_argument("--no-spot", action="store_true", help="Skip querying spot balances")
    parser.add_argument("--no-perp", action="store_true", help="Skip querying perp positions")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    info = Info(args.base_url, skip_ws=True)
    try:
        balances = info.user_balances(
            args.address,
            include_spot=not args.no_spot,
            include_perp=not args.no_perp,
            include_zero=args.include_zero,
        )
    except (ClientError, ServerError, RequestException) as exc:
        print(f"Error retrieving balances: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(balances, indent=2))
        return 0

    print(f"Address: {balances['address']}")
    print()

    perp = balances.get("perp")
    if perp:
        _print_perp(perp)
        print()

    spot = balances.get("spot")
    if spot:
        _print_spot(spot)
        print()

    if not perp and not spot:
        print("No balance data returned.")

    return 0


if __name__ == "__main__":  # pragma: no cover - entrypoint
    sys.exit(main())
