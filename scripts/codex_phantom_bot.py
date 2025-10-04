#!/usr/bin/env python3
"""CLI helper for preparing Codex phantom bot payloads.

The tool wraps :func:`hyperliquid.utils.phantom_bot.prepare_phantom_session`
and prints a JSON summary that can be fed to orchestration bots or manual
signers.  By default the action is read from ``stdin``; supply
``--action-file`` to load from disk instead.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from hyperliquid.utils.phantom_bot import prepare_phantom_session
from hyperliquid.utils.signing import get_timestamp_ms


def _load_action(path: Path | None) -> Dict[str, Any]:
    if path is None:
        return json.load(sys.stdin)

    if str(path) == "-":
        return json.load(sys.stdin)

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Codex phantom bot session payloads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/codex_phantom_bot.py --action-file action.json\\n"
            "  python scripts/codex_phantom_bot.py --vault-address 0xabc --mainnet < action.json"
        ),
    )
    parser.add_argument(
        "--action-file",
        type=Path,
        default=None,
        help="Path to the JSON action payload. Omit or pass '-' to read from stdin.",
    )
    parser.add_argument(
        "--vault-address",
        type=str,
        default=None,
        help="Optional vault address to include when computing the phantom agent payload.",
    )
    parser.add_argument(
        "--nonce",
        type=int,
        default=None,
        help="Timestamp (ms) nonce. Defaults to the current timestamp.",
    )
    parser.add_argument(
        "--expires-after",
        type=int,
        default=None,
        help="Optional expiry timestamp in milliseconds.",
    )
    env_group = parser.add_mutually_exclusive_group()
    env_group.add_argument("--mainnet", action="store_true", help="Prepare payloads for mainnet (default testnet).")
    env_group.add_argument("--testnet", action="store_true", help="Force testnet payloads (default).")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional file to write the JSON summary to in addition to stdout.",
    )
    parser.add_argument(
        "--dump-typed-data",
        type=Path,
        default=None,
        help="Write the typed EIP-712 payload to a dedicated file after hex encoding bytes.",
    )
    parser.add_argument(
        "--no-typed-data",
        action="store_true",
        help="Exclude the typedData block from the stdout summary.",
    )
    parser.add_argument(
        "--no-action",
        action="store_true",
        help="Exclude the original action from the stdout summary.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output with an indentation of two spaces.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    action = _load_action(args.action_file)
    nonce = args.nonce if args.nonce is not None else get_timestamp_ms()
    is_mainnet = args.mainnet and not args.testnet

    session = prepare_phantom_session(
        action,
        args.vault_address,
        nonce,
        args.expires_after,
        is_mainnet=is_mainnet,
    )

    summary = session.as_dict(
        include_typed_data=not args.no_typed_data,
        include_action=not args.no_action,
    )

    json_kwargs: Dict[str, Any] = {"ensure_ascii": False}
    if args.pretty:
        json_kwargs.update(indent=2, sort_keys=True)

    output_text = json.dumps(summary, **json_kwargs)
    print(output_text)

    if args.output:
        args.output.write_text(output_text + "\n", encoding="utf-8")

    if args.dump_typed_data:
        typed_summary = session.as_dict(include_action=False)
        typed_text = json.dumps(typed_summary.get("typedData", {}), **json_kwargs)
        args.dump_typed_data.write_text(typed_text + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())