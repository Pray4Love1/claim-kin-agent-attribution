#!/usr/bin/env python3
"""CLI helper for appending signed claims to the Codex registry."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Mapping


def _load_claim(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _ensure_total_owed(payload: Dict[str, Any]) -> None:
    if "total_owed_usd" in payload:
        return
    flows = payload.get("flow_estimates")
    rates = payload.get("royalty_rates")
    if not isinstance(flows, Mapping) or not isinstance(rates, Mapping):
        raise ValueError("Claim payload is missing flow or royalty information")

    total = 0.0
    for key, value in flows.items():
        if key not in rates:
            raise ValueError(f"No royalty rate provided for flow '{key}'")
        total += float(value) * float(rates[key])
    payload["total_owed_usd"] = round(total, 2)


def _compute_claim_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True).encode("utf-8")
    return sha256(canonical).hexdigest()


def create_registry_entry(
    claim_path: Path,
    signature: str,
    *,
    hash_file: Path | None = None,
    verified: bool = False,
) -> Dict[str, Any]:
    payload = _load_claim(claim_path)
    _ensure_total_owed(payload)
    claim_hash = _compute_claim_hash(payload)

    if hash_file is not None:
        if not hash_file.exists():
            raise FileNotFoundError(f"Hash file not found: {hash_file}")
        recorded_hash = hash_file.read_text(encoding="utf-8").strip()
        if recorded_hash and recorded_hash != claim_hash:
            raise ValueError("Hash file contents do not match the claim payload")

    entry: Dict[str, Any] = {
        "protocol": payload.get("protocol", ""),
        "linked_wallet": payload.get("linked_wallet", ""),
        "total_owed_usd": payload.get("total_owed_usd"),
        "claim_path": str(claim_path),
        "claim_hash": claim_hash,
        "signature": signature,
        "verified": bool(verified),
    }
    if hash_file is not None:
        entry["hash_file"] = str(hash_file)
    return entry


def _load_registry(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, list):
        return list(data)
    raise ValueError(f"Registry file {path} is not a JSON list")


def upsert_registry_entry(path: Path, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    registry = _load_registry(path)
    replaced = False
    for index, existing in enumerate(registry):
        if existing.get("claim_path") == entry["claim_path"]:
            registry[index] = entry
            replaced = True
            break
    if not replaced:
        registry.append(entry)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(registry, file, indent=2)
        file.write("\n")
    return registry


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
        "--registry",
        type=Path,
        default=Path("codex_registry.json"),
        help="Registry file to update",
    )
    parser.add_argument(
        "--verified",
        action="store_true",
        help="Mark the registry entry as verified",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    entry = create_registry_entry(args.claim, args.signature, hash_file=args.hash_file, verified=args.verified)
    upsert_registry_entry(args.registry, entry)
    print(f"[✅] Claim {args.claim} recorded in {args.registry}")
    print(f"[🔏] Signature: {args.signature}")
    print(f"[💰] Total owed (USD): {entry['total_owed_usd']:.2f}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
