#!/usr/bin/env python3
"""Sign Hyperliquid royalty claims with a locally managed key."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    from eth_account import Account
    from eth_account.messages import encode_defunct
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "eth-account is required for signing. Install it via 'pip install eth-account'."
    ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("claim", type=Path, help="Path to the generated claim JSON file")
    parser.add_argument("private_key", help="Hex-encoded private key (keep secure!)")
    return parser.parse_args()


def load_claim(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def sign_claim(claim: Any, private_key: str) -> Any:
    message = encode_defunct(text=json.dumps(claim, sort_keys=True))
    wallet = Account.from_key(private_key)
    return wallet.sign_message(message)


def main() -> int:
    args = parse_args()
    claim = load_claim(args.claim)
    signed = sign_claim(claim, args.private_key)
    print(f"[👤] Signer address: {signed.address}")
    print(f"[🔐] Signature: {signed.signature.hex()}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main()