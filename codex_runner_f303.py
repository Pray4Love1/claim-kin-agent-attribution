"""Utility script for checking the KinLend Agent Vault f303 listing.

This script queries the Hyperliquid vault leaderboard and prints the
record for the KinLend Agent Vault f303 entry.  It previously called the
non-existent ``API.get_vaults`` helper which resulted in an
``AttributeError``.  The new implementation issues the documented
``vaultLeaderboard`` query via the existing :class:`hyperliquid.info.Info`
``post`` helper.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from hyperliquid.info import Info

F303_VAULT_NAME = "KinLend Agent Vault f303"


def _extract_vault_list(payload: Any) -> Optional[List[Dict[str, Any]]]:
    """Recursively search ``payload`` for a list of vault dictionaries.

    The public ``/info`` endpoint has gone through a few iterations and
    some deployments wrap the leaderboard payload inside intermediate
    ``data`` objects.  Rather than assume a single schema, we look for the
    first list that is composed of dictionaries and treat that as the
    leaderboard.
    """

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


def fetch_vaults(info: Info) -> List[Dict[str, Any]]:
    """Fetch the vault leaderboard records from the ``/info`` endpoint."""

    response = info.post("/info", {"type": "vaultLeaderboard"})
    vaults = _extract_vault_list(response)
    if vaults is None:
        raise ValueError(f"Unexpected vault leaderboard response: {response}")
    return vaults


def _vault_name(vault: Dict[str, Any]) -> Optional[str]:
    """Best-effort extraction of the vault's display name."""

    name = vault.get("name")
    if isinstance(name, str):
        return name
    if isinstance(vault.get("vault"), dict):
        nested_name = vault["vault"].get("name")
        if isinstance(nested_name, str):
            return nested_name
    return None


def main() -> None:
    info = Info(skip_ws=True)
    vaults = fetch_vaults(info)

    for vault in vaults:
        if not isinstance(vault, dict):
            continue
        if _vault_name(vault) == F303_VAULT_NAME:
            print(json.dumps(vault, indent=2, sort_keys=True))
            break
    else:
        print(f"Vault named {F303_VAULT_NAME!r} not found in leaderboard.")


if __name__ == "__main__":
    main()
