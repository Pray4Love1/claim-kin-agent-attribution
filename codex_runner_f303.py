#!/usr/bin/env python3
<<<<<<< HEAD
"""Codex verifier for f303 attribution.

Pulls vault leaderboard + withdrawable balance + verifies f303_attribution.json
"""

from __future__ import annotations
import argparse
import json
import os
from decimal import Decimal, InvalidOperation
from pprint import pprint
from typing import Any, Dict

from hyperliquid.info import Info
from hyperliquid.utils import constants

DEFAULT_VAULT_ID = "f303"
DEFAULT_OWNER_ADDRESS = "0xcd5051944f780a621ee62e39e493c489668acf4d"
ATTRIBUTION_FILE = "f303_attribution.json"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch the f303 vault leaderboard and verify attribution claim."
    )
    parser.add_argument(
        "--vault-id",
        default=DEFAULT_VAULT_ID,
        help="Hyperliquid vault ID (default: f303)",
    )
    parser.add_argument(
        "--owner-address",
        required=True,
        help="Vault owner address (real withdrawal controller)",
    )
    parser.add_argument(
        "--base-url",
        default=constants.MAINNET_API_URL,
        help="Hyperliquid API base URL (default: mainnet)",
    )
    return parser.parse_args()

def fetch_leaderboard(info: Info, vault_id: str) -> Dict[str, Any]:
    payload = {"type": "vaultLeaderboard", "vault": vault_id}
    leaderboard = info.post("/info", payload)
    if not isinstance(leaderboard, dict):
        raise TypeError(f"Unexpected leaderboard response: {type(leaderboard)}")
    return leaderboard

def format_withdrawable(raw_withdrawable: Any) -> str:
    if raw_withdrawable is None:
        return "Withdrawable amount unavailable."
    try:
        wd = Decimal(str(raw_withdrawable))
    except (InvalidOperation, ValueError):
        return f"Withdrawable (unparsed): {raw_withdrawable}"
    return f"Withdrawable: {wd.normalize()}"

def verify_attribution(owner_address: str, vault_id: str):
    if not os.path.exists(ATTRIBUTION_FILE):
        print("⚠️  No attribution file found. Skipping verification.")
        return

    with open(ATTRIBUTION_FILE) as f:
        data = json.load(f)

    claimer = data.get("claimer", "").lower()
    claimed_vault = data.get("vault", "").lower()

    match_claimer = "✅" if claimer == owner_address.lower() else "❌"
    match_vault = "✅" if claimed_vault.endswith(vault_id.lower()) else "❌"

    print("\n📂 Attribution file loaded:")
    print(f" - Claimer: {claimer} {match_claimer}")
    print(f" - Vault:   {claimed_vault} {match_vault}")

    if match_claimer == "❌":
        print("⚠️  Claimer does NOT match --owner-address. Update your claim.")
    if match_vault == "❌":
        print("⚠️  Vault ID in claim does not match actual vault.")

def main() -> None:
    args = parse_args()
    info = Info(args.base_url, skip_ws=True)

    print(f"📊 Leaderboard for vault '{args.vault_id}' at {args.base_url}...\n")
    leaderboard = fetch_leaderboard(info, args.vault_id)
    pprint(leaderboard)

    print(f"\n🔐 Checking clearinghouse state for: {args.owner_address}")
    state = info.user_state(args.owner_address)
    if not isinstance(state, dict):
        print("❌ Invalid user state.")
        return

    print(f"\n💰 {format_withdrawable(state.get('withdrawable'))}")
    verify_attribution(args.owner_address, args.vault_id)
=======
"""Codex runner that locates the KinLend f303 vault on Hyperliquid."""

import json
from typing import Any, Dict, List

from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL

F303_VAULT_ADDRESS = "0xdfC24b077bC1425Ad1DeA75BCB6F8158E10Df303"
F303_SUFFIX = "f303"


def fetch_vaults(client: Info) -> List[Dict[str, Any]]:
    """Fetch the list of vaults from the Hyperliquid info endpoint."""
    payload = client.post("/info", {"type": "vaultLeaderboard"})
    vaults = _extract_vaults(payload)
    if not isinstance(vaults, list):
        raise RuntimeError(f"Unexpected vault leaderboard payload: {payload!r}")
    return [vault for vault in vaults if isinstance(vault, dict)]


def _extract_vaults(payload: Any) -> Any:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("vaults"), list):
            return payload["vaults"]
        for key in ("leaderboard", "data", "result"):
            inner = payload.get(key)
            if isinstance(inner, dict) and isinstance(inner.get("vaults"), list):
                return inner["vaults"]
            if isinstance(inner, list):
                return inner
    return None


def _is_f303_vault(vault: Dict[str, Any]) -> bool:
    address = str(
        vault.get("vaultAddress")
        or vault.get("address")
        or vault.get("id")
        or ""
    ).lower()
    name = str(vault.get("name") or vault.get("vaultName") or vault.get("displayName") or "").lower()
    return (
        address == F303_VAULT_ADDRESS.lower()
        or address.endswith(F303_SUFFIX)
        or name.endswith(F303_SUFFIX)
        or F303_SUFFIX in name
    )


def _format_vault(vault: Dict[str, Any]) -> str:
    address = vault.get("vaultAddress") or vault.get("address") or vault.get("id") or "<unknown address>"
    name = vault.get("name") or vault.get("vaultName") or vault.get("displayName") or "<unnamed vault>"
    manager = vault.get("manager") or vault.get("owner") or vault.get("operator")
    aum = vault.get("aum") or vault.get("vaultEquity") or vault.get("assetsUnderManagement") or vault.get("tvl")
    apy = vault.get("apy") or vault.get("apyPct") or vault.get("apy7d") or vault.get("apy30d")

    parts: List[str] = [f"Vault: {name} ({address})"]
    if manager:
        parts.append(f"  • Manager: {manager}")
    if aum is not None:
        parts.append(f"  • AUM: {aum}")
    if apy is not None:
        parts.append(f"  • APY: {apy}")
    parts.append(f"  • Raw: {json.dumps(vault, indent=2)}")
    return "\n".join(parts)


def main() -> None:
    info = Info(MAINNET_API_URL, skip_ws=True)
    vaults = fetch_vaults(info)
    print(f"📊 Retrieved {len(vaults)} vault entries from Hyperliquid.")

    f303_vaults = [vault for vault in vaults if _is_f303_vault(vault)]
    if not f303_vaults:
        print("⚠️ No vault entries matched the f303 identifier.")
        return

    print("\n🎯 f303 vault matches:")
    for vault in f303_vaults:
        print(_format_vault(vault))
        print()

>>>>>>> keeper-backup

if __name__ == "__main__":
    main()
