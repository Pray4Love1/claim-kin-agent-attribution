#!/usr/bin/env python3
"""High-level wrapper around :mod:`codex_enforce` for withdrawal verification."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

from codex_enforce import _ensure_total_owed, _load_claim, validate_hash, verify_signature


def enforce_claim(
    *,
    claim_path: Path,
    signature: str,
    expected_signer: str | None = None,
    hash_file: Path | None = None,
    claim_hash: str | None = None,
) -> Dict[str, Any]:
    payload = _load_claim(claim_path)
    _ensure_total_owed(payload)
    hash_value = validate_hash(payload, hash_file)
    if claim_hash and hash_value.lower() != claim_hash.lower():
        raise ValueError("Computed claim hash does not match --claim-hash")

    is_valid, recovered = verify_signature(payload, signature, expected_signer)
    return {
        "hash": hash_value,
        "payload": payload,
        "is_valid": is_valid,
        "recovered": recovered,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--claim",
        type=Path,
        default=Path("claims/royalty_claim_hyperliquid.json"),
        help="Claim JSON to verify. Defaults to the Hyperliquid royalty claim output.",
    )
    parser.add_argument("--signature", required=True, help="Keeper signature authorising the withdrawal")
    parser.add_argument("--expected-signer", help="Optional expected signer address")
    parser.add_argument("--hash-file", type=Path, default=None, help="Optional claim hash file to validate")
    parser.add_argument("--claim-hash", help="Optional expected hash string when the hash file is unavailable")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = enforce_claim(
            claim_path=args.claim,
            signature=args.signature,
            expected_signer=args.expected_signer,
            hash_file=args.hash_file,
            claim_hash=args.claim_hash,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"[❌] {exc}")
        return 1

    payload = result["payload"]
    hash_value = result["hash"]
    recovered = result["recovered"]
    is_valid = result["is_valid"]

    total = payload.get("total_owed_usd", "unknown")
    if isinstance(total, (int, float)):
        total_str = f"{total:.2f}"
    else:
        total_str = str(total)

    status = "✅" if is_valid else "⚠️"
    print(f"[🔒] Claim hash: {hash_value}")
    print(f"[👤] Recovered signer: {recovered}")
    print(f"[💰] Total owed (USD): {total_str}")
    if args.expected_signer:
        if is_valid:
            print(f"{status} Signature matches expected signer {args.expected_signer}")
        else:
            print(f"{status} Signature does not match expected signer {args.expected_signer}")
            return 1
    else:
        print("[ℹ️] No expected signer supplied; verification limited to recovery")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())