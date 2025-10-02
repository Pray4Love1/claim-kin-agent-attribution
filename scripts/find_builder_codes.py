#!/usr/bin/env python3
"""List builder referral codes available on Hyperliquid."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from hyperliquid.info import Info
from hyperliquid.utils import constants

from claim_kin_agent_attribution.builder_codes import (
    BuilderCode,
    fetch_builder_codes,
    filter_builder_codes,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect the available builder-deployed perp DEX configurations and "
            "extract referral codes, share allocations, and builder addresses."
        )
    )
    parser.add_argument(
        "--api-url",
        default=constants.MAINNET_API_URL,
        help="Hyperliquid API endpoint to query (defaults to mainnet).",
    )
    parser.add_argument(
        "--builder",
        action="append",
        dest="builders",
        default=[],
        help="Filter results to the specified builder address. Repeat for multiple addresses.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a formatted table.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the JSON payload produced by --json.",
    )
    return parser


def _format_line(code: BuilderCode) -> str:
    share = f"{code.share_bps} bps" if code.share_bps is not None else "—"
    referral = code.code or "—"
    return f"{code.dex:20} | {code.builder_address} | {referral:10} | {share}"


def _emit_json(codes: Sequence[BuilderCode], stream, output: Path | None) -> None:
    payload = [code.as_dict() for code in codes]
    document = {"count": len(codes), "builder_codes": payload}
    json.dump(document, stream, indent=2)
    stream.write("\n")
    if output is not None:
        output.write_text(json.dumps(document, indent=2) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    info = Info(args.api_url, skip_ws=True)
    codes = fetch_builder_codes(info)
    filtered = filter_builder_codes(codes, args.builders)

    if args.json or args.output is not None:
        _emit_json(filtered, sys.stdout, args.output)
        return 0

    if not filtered:
        print("No builder codes found for the requested filters.")
        return 0

    print("DEX                 | Builder Address                       | Code       | Share")
    print("-" * 86)
    for code in filtered:
        print(_format_line(code))
    return 0


if __name__ == "__main__":
    sys.exit(main())
