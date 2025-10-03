#!/usr/bin/env python3
"""Codex runner that locates the KinLend f303 vault on Hyperliquid.

Run with ``python codex_runner_f303.py --owner-address <vault_owner>`` to
override the default vault owner address. Supplying the current owner address
ensures the withdrawable amount fetched from ``Info.user_state`` stays
accurate.
"""

import argparse
import json
from typing import Any, Dict, List, Optional

from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL

F303_VAULT_ADDRESS = "0xdfC24b077bC1425Ad1DeA75BCB6F8158E10Df303"
F303_SUFFIX = "f303"
DEFAULT_OWNER_ADDRESS = "0x996994D2914DF4eEE6176FD5eE152e2922787EE7"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Locate the KinLend f303 vault and inspect its clearinghouse state.")
    parser.add_argument(
        "--owner-address",
        default=DEFAULT_OWNER_ADDRESS,
        help=(
            "Vault owner address to query via Info.user_state. "
            "Use the latest vault manager address to keep withdrawable data accurate."
        ),
    )
    return parser.parse_args()


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
    args = parse_args()
    info = Info(MAINNET_API_URL, skip_ws=True)
    vaults = fetch_vaults(info)
    print(f"📊 Retrieved {len(vaults)} vault entries from Hyperliquid.")

    f303_vaults = [vault for vault in vaults if _is_f303_vault(vault)]
    if not f303_vaults:
        print("⚠️ No vault entries matched the f303 identifier.")
    else:
        print("\n🎯 f303 vault matches:")
        for vault in f303_vaults:
            print(_format_vault(vault))
            print()

    state = info.user_state(args.owner_address)
    withdrawable = _extract_withdrawable(state)
    if withdrawable is None:
        print(
            "ℹ️  Clearinghouse state queried, but no withdrawable field was present in the response."
        )
    else:
        print(f"🏦 Withdrawable balance for {args.owner_address}: {withdrawable}")


def _extract_withdrawable(state: Any) -> Optional[Any]:
    if isinstance(state, dict):
        if state.get("withdrawable") is not None:
            return state["withdrawable"]
        margin_summary = state.get("marginSummary")
        if isinstance(margin_summary, dict) and margin_summary.get("withdrawable") is not None:
            return margin_summary["withdrawable"]
    return None


if __name__ == "__main__":
    main()
