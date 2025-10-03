#!/usr/bin/env python3
"""Codex runner for f303 attribution.
Safely probes Hyperliquid API, fetches meta, and attempts vault lookups.
"""

import argparse
import json
from typing import Any, Dict, Optional

from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL


DEFAULT_OWNER = "0xcd5051944f780a621ee62e39e493c489668acf4d"
DEFAULT_VAULT_ID = "f303"


def parse_args():
    parser = argparse.ArgumentParser(description="Codex f303 vault attribution runner")
    parser.add_argument(
        "owner_address",
        help="Vault owner address (controller of f303)",
    )
    parser.add_argument(
        "--base-url",
        default=MAINNET_API_URL,
        help="Hyperliquid API base URL (default: mainnet)",
    )
    parser.add_argument(
        "--vault-id",
        default=DEFAULT_VAULT_ID,
        help="Vault ID to check (default: f303)",
    )
    return parser.parse_args()


def safe_post(info: Info, url_path: str, payload: Dict[str, Any]) -> Optional[Any]:
    """Wrapper that catches 'deserialize' errors cleanly."""
    try:
        return info.post(url_path, payload)
    except Exception as e:
        msg = str(e)
        if "Failed to deserialize" in msg:
            print(f"⚠️ Endpoint does not support payload {payload}")
            return None
        print(f"❌ Request failed for {payload}: {e}")
        return None


def main():
    args = parse_args()
    info = Info(args.base_url, skip_ws=True)

    print("🔍 Probing API health with {\"type\":\"meta\"}...")
    meta = safe_post(info, "/info", {"type": "meta"})
    if meta:
        print("✅ Meta response OK")
        print(json.dumps(meta, indent=2)[:500] + "...\n")  # show first 500 chars

    print(f"📊 Fetching leaderboard for vault {args.vault_id}...")
    payloads = [
        {"type": "vaultLeaderboard"},
        {"type": "vaultLeaderboard", "vault": args.vault_id},
        {"type": "vaultLeaderboard", "vaultId": args.vault_id},
    ]
    leaderboard = None
    for p in payloads:
        leaderboard = safe_post(info, "/info", p)
        if leaderboard:
            print(f"✅ Got leaderboard with {p}")
            print(json.dumps(leaderboard, indent=2))
            break
    if not leaderboard:
        print("⚠️ Vault leaderboard is not available on this API. "
              "Use trader/clearinghouse API instead of api.hyperliquid.xyz.\n")

    print(f"🔐 Checking user_state for {args.owner_address}...")
    state = safe_post(info, "/info", {"type": "clearinghouseState", "user": args.owner_address})
    if state:
        print("✅ Clearinghouse state:")
        print(json.dumps(state, indent=2))
    else:
        print("⚠️ Could not fetch clearinghouse state here. "
              "Try trader API instead of api.hyperliquid.xyz.")


if __name__ == "__main__":
    main()
