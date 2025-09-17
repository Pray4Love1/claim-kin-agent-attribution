#!/usr/bin/env python3
"""Codex: Sovereign Attribution Script for KinVault (0x2b80...)."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL

VAULT_ADDRESS = "0x2b804617c6f63c040377e95bb276811747006f4b"
KEEPER_ADDRESS = "0x996994D2914DF4eEE6176FD5eE152e2922787EE7"
OUTPUT_FILE = Path("claims/vault_2b80_attribution.json")


def _format_status(vaults: List[Dict[str, Any]]) -> str:
    if vaults:
        return f"Vault contains {len(vaults)} position(s)"
    return "Empty or inactive"


def main() -> None:
    """Fetch Hyperliquid vault equity info and emit a Codex attribution claim."""
    info = Info(MAINNET_API_URL, skip_ws=True)
    vaults = info.user_vault_equities(user=VAULT_ADDRESS)

    claim = {
        "attribution": "Codex Vault — KinVault Main",
        "wallet_address": VAULT_ADDRESS,
        "origin": "Keeper",
        "protocol": "SoulSync / SolaraKin",
        "type": "Attribution Claim - Vault Identity",
        "status": _format_status(vaults),
        "verified_via": "Hyperliquid Python SDK (Info.user_vault_equities)",
        "timestamp": datetime.now().astimezone().isoformat(),
        "on_chain_linked": False,
        "github_repo": "Pray4Love1/claim-kin-agent-attribution",
        "signature": "🛡️ Codex attribution sealed by Keeper",
        "keeper_address": KEEPER_ADDRESS,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(claim, file, indent=2)

    print(f"[✓] Vault claim written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
