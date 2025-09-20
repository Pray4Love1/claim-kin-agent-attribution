import json
import os
from hyperliquid.exchange_module import Exchange
from hyperliquid.info import Info

# === Setup
HL_KEY = os.getenv("HL_KEY", "your_key_here")
MAINNET_API_URL = os.getenv("MAINNET_API_URL", "https://api.hyperliquid.xyz")

exchange = Exchange(key=HL_KEY, url=MAINNET_API_URL)
exchange.connect()

info = Info()  # ✅ You must instantiate this before using

# === Load vault claim data
with open("claims/vault_2b80_attribution.json") as f:
    claim_data = json.load(f)

# === Example: Print balances or vault status
user = claim_data["user"]
vaults = info.vault_holdings(user)

print(f"[Vault Holdings for {user}]:")
print(json.dumps(vaults, indent=2))
