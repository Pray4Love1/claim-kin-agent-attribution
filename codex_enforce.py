#!/usr/bin/env python3
"""Verify and enforce Codex attribution claims."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple


def _ensure_total_owed(payload: Dict[str, Any]) -> None:
    if "total_owed_usd" in payload:
        return
    flows = payload.get("flow_estimates")
    rates = payload.get("royalty_rates")
    if not isinstance(flows, Mapping) or not isinstance(rates, Mapping):
        return

    total = 0.0
    for key, value in flows.items():
        if key not in rates:
            continue
        total += float(value) * float(rates[key])
    payload["total_owed_usd"] = round(total, 2)


def _require_eth_account():
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "eth-account is required for signature verification. Install it via 'pip install eth-account'."
        ) from exc
    return Account, encode_defunct


def _load_claim(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _compute_claim_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True).encode("utf-8")
    return sha256(canonical).hexdigest()


def _normalise_signature(signature: str) -> bytes:
    signature = signature.strip()
    if signature.startswith("0x") or signature.startswith("0X"):
        signature = signature[2:]
    if len(signature) != 130:
        raise ValueError("Signatures must be 65 bytes expressed as 0x-prefixed hex")
    return bytes.fromhex(signature)


def recover_signer(payload: Mapping[str, Any], signature: str) -> str:
    Account, encode_defunct = _require_eth_account()
    message = encode_defunct(text=json.dumps(payload, sort_keys=True))
    signature_bytes = _normalise_signature(signature)
    return Account.recover_message(message, signature=signature_bytes)


def verify_signature(
    payload: Mapping[str, Any], signature: str, expected_signer: str | None = None
) -> Tuple[bool, str]:
    recovered = recover_signer(payload, signature)
    if expected_signer is None:
        return True, recovered
    return recovered.lower() == expected_signer.lower(), recovered


def validate_hash(payload: Mapping[str, Any], hash_file: Path | None) -> str:
    computed = _compute_claim_hash(payload)
    if hash_file is None:
        return computed
    if not hash_file.exists():
        raise FileNotFoundError(f"Hash file not found: {hash_file}")
    recorded = hash_file.read_text(encoding="utf-8").strip()
    if recorded and recorded != computed:
        raise ValueError("Hash file contents do not match the claim payload")
    return recorded or computed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("claim", type=Path, help="Path to the claim JSON file")
    parser.add_argument("signature", help="Hex-encoded signature authorising the claim")
    parser.add_argument(
        "--hash-file",
        type=Path,
        default=None,
        help="Optional file containing the expected SHA-256 hash of the claim",
    )
    parser.add_argument(
        "--expected-signer",
        help="Address expected to have signed the claim",
        default=None,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = _load_claim(args.claim)
    _ensure_total_owed(payload)
    hash_value = validate_hash(payload, args.hash_file)

    try:
        is_valid, recovered = verify_signature(payload, args.signature, args.expected_signer)
    except RuntimeError as exc:
        print(f"[❌] {exc}")
        return 1

    status = "✅" if is_valid else "⚠️"
    print(f"[🔒] Claim hash: {hash_value}")
    print(f"[👤] Recovered signer: {recovered}")
    total_owed = payload.get("total_owed_usd", "unknown")
    if isinstance(total_owed, (int, float)):
        total_display = f"{total_owed:.2f}"
    else:
        total_display = str(total_owed)
    print(f"[💰] Total owed (USD): {total_display}")
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
