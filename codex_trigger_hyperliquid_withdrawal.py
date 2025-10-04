"""Trigger a Hyperliquid withdrawal from the command line.

This script is intentionally kept simple so it can be executed directly via
```
python codex_trigger_hyperliquid_withdrawal.py
```

It validates the required environment variables, checks the balance for the
configured token, and then submits a withdrawal if sufficient funds exist.
"""

import os
import sys

from dotenv import load_dotenv

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants


def main() -> None:
    """Check balances and trigger a Hyperliquid withdrawal."""

    # === Load your secret key from Codex secrets ===
    load_dotenv()
    api_private_key = os.getenv("HYPERLIQUID_API_PRIVATE_KEY")
    if not api_private_key:
        raise ValueError("HYPERLIQUID_API_PRIVATE_KEY not found in .env or Codex secrets.")

    # === Your main Arbitrum wallet ===
    main_address = "0x996994D2914DF4EeE6176fD5eE152E2922787Ee7"  # ✅ Replace if needed
    destination = main_address

    # === Token and Amount ===
    token = "USDC"
    amount = 6_000_000.0  # 🔁 Change this if needed

    # === Use MAINNET URL ===
    api_url = constants.MAINNET_API_URL

    # === Step 1: Check available balance ===
    info = Info(api_url, skip_ws=True)
    try:
        state = info.user_state(main_address)
        balances = state.get("assetPositions", [])
        usdc = next((item["szi"] for item in balances if item["coin"] == token), 0)
        print(f"🔍 Available {token}: {usdc}")
        if float(usdc) < float(amount):
            raise ValueError(f"❌ Not enough {token} (needed: {amount}, available: {usdc})")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Balance check error: {exc}")
        sys.exit(1)

    # === Step 2: Trigger withdrawal ===
    exchange = Exchange(api_private_key, base_url=api_url, account_address=main_address)
    try:
        print(f"🚀 Requesting withdrawal of {amount} {token} to {destination}...")
        result = exchange.spot_send(destination, token, amount)
        print("✅ Withdrawal submitted:")
        print(result)

        if result.get("status") == "ok":
            msg_hash = result.get("response", {}).get("data", {}).get("message")
            print(f"📦 Withdrawal message hash: {msg_hash}")
            print("⏳ Wait ~5 minutes for finalization (batchedFinalizeWithdrawals)")
            print("🔗 View on Arbiscan or app.hyperliquid.xyz")
        else:
            print(f"❌ Withdrawal failed: {result.get('error')}")
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ Error during withdrawal: {exc}")


if __name__ == "__main__":
    main()
