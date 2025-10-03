import os
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# 🔐 Load private key
private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
if not private_key:
    raise ValueError("Set HYPERLIQUID_PRIVATE_KEY environment variable")

# 🌐 API URL
# Use TESTNET_API_URL for testing or MAINNET_API_URL for real funds
API_URL = constants.MAINNET_API_URL

# ⚙️ Initialize exchange (signing handled internally)
exchange = Exchange(private_key, base_url=API_URL)

# 💸 Withdrawal details
destination = "0xcd5051944f780a621ee62e39e493c489668acf4d"  # your vault/recipient wallet
token = "USDC"                                              # withdrawing USDC
amount = 100.0                                              # example: withdraw 100 USDC

# 🚀 Initiate withdrawal
result = exchange.spot_send(destination, token, amount)
print(f"Withdrawal result: {result}")
