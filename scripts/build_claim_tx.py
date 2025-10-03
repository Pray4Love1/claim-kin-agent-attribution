#!/usr/bin/env python3
"""Assemble calldata for VaultScannerV2WithSig ``claimVaultWithSig`` invocations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from claims.vault_scanner_utils import build_claim_vault_with_sig_transaction


def _load_default_user(claim_file: Path | None) -> str | None:
    if claim_file is None:
        return None
    if not claim_file.exists():
        return None
    try:
        payload = json.loads(claim_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    linked_wallet = payload.get("linked_wallet")
    if isinstance(linked_wallet, str) and linked_wallet:
        return linked_wallet
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-address", required=True, help="Target VaultScanner contract address")
    parser.add_argument("--vault-id", required=True, help="Vault identifier (bytes32 hex string)")
    parser.add_argument("--balance", required=True, type=int, help="Vault balance encoded as uint256")
    parser.add_argument("--attribution-hash", required=True, help="Attribution hash (bytes32 hex string)")
    parser.add_argument("--signature", required=True, help="Keeper signature authorising the claim")
    parser.add_argument(
        "--user",
        help="Beneficiary wallet address. Defaults to the linked wallet from the claim JSON if available.",
    )
    parser.add_argument(
        "--claim-file",
        type=Path,
        default=Path("claims/royalty_claim_hyperliquid.json"),
        help="Claim JSON used to infer the linked wallet when --user is not supplied.",
    )
    parser.add_argument("--chain-id", type=int, default=None, help="Optional EVM chain identifier")
    parser.add_argument("--gas", type=int, default=None, help="Optional gas limit to embed in the transaction")
    parser.add_argument("--nonce", type=int, default=None, help="Optional nonce to embed in the transaction")
    parser.add_argument(
        "--sender",
        help="Optional sender override. Defaults to the user wallet when omitted.",
    )
    return parser.parse_args()


def build_claim_transaction_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    user = args.user or _load_default_user(args.claim_file)
    if not user:
        raise ValueError("Unable to determine beneficiary address. Provide --user explicitly or a valid claim file.")

    sender = args.sender or user

    transaction = build_claim_vault_with_sig_transaction(
        user=user,
        vault_id=args.vault_id,
        balance=args.balance,
        attribution_hash=args.attribution_hash,
        signature=args.signature,
        contract_address=args.vault_address,
        sender=sender,
        chain_id=args.chain_id,
        gas=args.gas,
        nonce=args.nonce,
    )
    return transaction


def main() -> int:
    args = parse_args()
    try:
        transaction = build_claim_transaction_from_args(args)
    except ValueError as exc:
        print(f"[❌] {exc}")
        return 1

    print("[✅] claimVaultWithSig transaction ready")
    print(json.dumps(transaction, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())