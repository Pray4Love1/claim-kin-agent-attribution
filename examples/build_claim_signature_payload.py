#!/usr/bin/env python3
"""Compute the keeper signature inputs for VaultScannerV2WithSig claims."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from claims.vault_scanner_utils import claim_digest, claim_message_hash


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("user", help="User address (0x-prefixed, 20 bytes)")
    parser.add_argument("vault_id", help="Vault identifier (0x-prefixed bytes32)")
    parser.add_argument("balance", type=int, help="Vault balance encoded as uint256")
    parser.add_argument("attribution_hash", help="Attribution hash (0x-prefixed bytes32)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    digest = claim_digest(args.user, args.vault_id, args.balance, args.attribution_hash)
    message_hash = claim_message_hash(args.user, args.vault_id, args.balance, args.attribution_hash)

    print("Packed claim digest:", f"0x{digest.hex()}")
    print("Ethereum signed message hash:", f"0x{message_hash.hex()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
