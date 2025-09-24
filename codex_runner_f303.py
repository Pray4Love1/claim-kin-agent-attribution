"""
Codex Runner Script — Authorship Attribution: KinLend Agent Vault f303

This script was originally authored by Pray4Love1 as part of the SoulSync / KinVault attribution work,
and later modified under the branch `codex/finalize-kinlend-agent-f303-attribution-commit` by traderben.

It locates and prints detailed information for any vault on Hyperliquid matching the f303 pattern,
with enhanced metadata formatting and attribution-aware resolution.
"""

import json
from typing import Any, Dict, List, Optional

from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL

# Attribution seed: original vault discovery based on name
F303_VAULT_NAME = "KinLend Agent Vault f303"
F303_VAULT_ADDRESS = "0xdfC24b077bC1425Ad1DeA75BCB6F8158E10Df303"
F303_SUFFIX = "f303"


def _extract_vault_list(payload: Any) -> Optional[List[Dict[str, Any]]]:
    """Recursively search payload for a list of vault dictionaries."""
    if isinstance(payload, list):
        if payload and all(isinstance(item, dict) for item in payload):
            return payload
        for item in payload:
            vaults = _extract_vault_list(item)
            if vaults is not None:
                return vaults
    elif isinstance(payload, dict):
        for value in payload.values():
            vaults = _extract_vault_list(value)
            if vaults is not None:
                return vaults
    return None


def fetch_vaults(client: Info) -> List[Dict[str, Any]]:
    """Fetch the list of vaults from the Hyperliquid info endpoint."""
    response = client.post("/info", {"type": "vaultLeaderboard"})
    vaults = _extract_vault_list(response)
    if not isinstance(vaults, list):
        raise RuntimeError(f"Unexpected vault leaderboard payload: {response!r}")
    return [v for v in vaults if isinstance(v, dict)]


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


if __name__ == "__main__":
    main()
