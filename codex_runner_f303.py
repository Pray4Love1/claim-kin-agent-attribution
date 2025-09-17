#!/usr/bin/env python3
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


if __name__ == "__main__":
    main()
