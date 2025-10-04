#!/usr/bin/env python3
"""Utility for crafting and signing Codex phantom agent actions.

This helper wraps the low-level primitives in :mod:`hyperliquid.utils.signing`
so that operators can derive the phantom agent payload that Codex submits to
Hyperliquid.  It accepts raw action JSON, derives the connection hash, and can
optionally sign the payload when provided with a private key.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_utils import to_hex

from hyperliquid.utils.signing import (
    sign_l1_action,
    action_hash,
    l1_payload,
)


def default_nonce() -> int:
    """Return the current UNIX timestamp in milliseconds."""

    return int(time.time() * 1000)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create the phantom agent payload that Codex submits to Hyperliquid. "
            "Provide the raw action JSON, and optionally sign it by supplying a private key."
        )
    )
    parser.add_argument(
        "action",
        nargs="?",
        help=(
            "Path to a JSON file containing the action to submit. "
            "If omitted, the tool reads JSON from stdin."
        ),
    )
    parser.add_argument(
        "--nonce",
        type=int,
        default=None,
        help=(
            "Nonce (timestamp in ms) to bind to the action. "
            "Defaults to the current time in milliseconds."
        ),
    )
    parser.add_argument(
        "--expires-after",
        type=int,
        default=None,
        help="Optional expiry timestamp (ms) that accompanies the action.",
    )
    parser.add_argument(
        "--vault-address",
        default=None,
        help="Optional vault address associated with the action.",
    )
    parser.add_argument(
        "--network",
        choices=["mainnet", "testnet"],
        default="mainnet",
        help="Select whether to build a mainnet (default) or testnet payload.",
    )
    parser.add_argument(
        "--private-key",
        default=None,
        help=(
            "Private key (hex) used to sign the payload. "
            "If omitted, the tool looks at the PRIVATE_KEY environment variable."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the phantom agent payload as JSON.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the resulting JSON payload when writing to stdout.",
    )
    return parser.parse_args()


def load_action(path_or_json: Optional[str]) -> Dict[str, Any]:
    if path_or_json:
        candidate = Path(path_or_json)
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8")
        else:
            text = path_or_json
    else:
        text = sys.stdin.read()

    try:
        action = json.loads(text)
    except json.JSONDecodeError as exc:  # pragma: no cover - CLI input validation
        raise SystemExit(f"Failed to parse action JSON: {exc}") from exc

    if not isinstance(action, dict):  # pragma: no cover - CLI input validation
        raise SystemExit("Action payload must be a JSON object.")

    return action


def resolve_private_key(arg_key: Optional[str]) -> Optional[str]:
    if arg_key:
        return arg_key
    env_key = os.getenv("PRIVATE_KEY")
    if env_key:
        return env_key
    return None


def get_wallet(private_key: str) -> LocalAccount:
    try:
        return Account.from_key(private_key)
    except ValueError as exc:  # pragma: no cover - CLI input validation
        raise SystemExit(f"Invalid private key: {exc}") from exc


def _jsonify(value: Any) -> Any:
    """Recursively convert complex values into JSON-friendly primitives."""

    if isinstance(value, bytes):
        return "0x" + value.hex()
    if isinstance(value, (list, tuple)):
        return [_jsonify(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonify(val) for key, val in value.items()}
    if hasattr(value, "_asdict"):
        return {key: _jsonify(val) for key, val in value._asdict().items()}
    return value


def build_payload(
    action: Dict[str, Any],
    nonce: int,
    expires_after: Optional[int],
    vault_address: Optional[str],
    is_mainnet: bool,
) -> Dict[str, Any]:
    """Construct the phantom agent payload without signing."""

    connection_hash = action_hash(action, vault_address, nonce, expires_after)
    phantom_agent = construct_phantom_agent(connection_hash, is_mainnet)
    typed_data = get_l1_action_data(action, vault_address, nonce, expires_after, is_mainnet)

    payload: Dict[str, Any] = {
        "network": "mainnet" if is_mainnet else "testnet",
        "nonce": nonce,
        "expiresAfter": expires_after,
        "vaultAddress": vault_address,
        "phantomAgent": {
            "source": phantom_agent["source"],
            "connectionId": to_hex(phantom_agent["connectionId"]),
        },
        "typedData": _jsonify(typed_data),
        "action": json.loads(json.dumps(action)),
    }
    return payload


def sign_payload(
    wallet: LocalAccount,
    action: Dict[str, Any],
    nonce: int,
    expires_after: Optional[int],
    vault_address: Optional[str],
    is_mainnet: bool,
) -> Dict[str, Any]:
    signature = sign_l1_action(wallet, action, vault_address, nonce, expires_after, is_mainnet)
    return {
        "address": wallet.address,
        "signature": signature,
    }


def main() -> None:
    args = parse_args()
    action = load_action(args.action)
    nonce = args.nonce if args.nonce is not None else default_nonce()
    payload = build_payload(action, nonce, args.expires_after, args.vault_address, args.network == "mainnet")

    private_key = resolve_private_key(args.private_key)
    if private_key:
        wallet = get_wallet(private_key)
        payload["signer"] = sign_payload(
            wallet,
            payload["action"],
            payload["nonce"],
            payload["expiresAfter"],
            payload["vaultAddress"],
            args.network == "mainnet",
        )

    serialized = json.dumps(payload, indent=2 if args.pretty else None, sort_keys=args.pretty)

    if args.output:
        args.output.write_text(serialized + ("\n" if not serialized.endswith("\n") else ""), encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
