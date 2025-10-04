# gasless_withdraw.py

import os
from hyperliquid.api import Exchange
from hyperliquid.utils.signing import sign_withdraw_from_bridge_action
from dotenv import load_dotenv

# Load secret key (Codex handles env injection automatically)
load_dotenv()
SECRET_KEY = os.getenv("KIN_AGENT_KEY") or os.getenv("PRIVATE_KEY") or os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise EnvironmentError("Missing KIN_AGENT_KEY, PRIVATE_KEY, or SECRET_KEY in environment.")

# Setup your subaccount and withdrawal details
subaccount_name = "default"  # or your actual subaccount name
token = "USDC"               # or "USDH", "ETH", etc.
amount = 6000000             # amount in token's native units (e.g. 6 USDC = 6000000)

# Receiver wallet (EVM address)
destination = "0xb2b297eF9449aa0905bC318B3bd258c4804BAd98"

# Initialize Hyperliquid SDK
exchange = Exchange(
    api_key=None, 
    secret_key=SECRET_KEY,
    subaccount=subaccount_name
)

# Trigger off-chain withdrawal
print(f"🔄 Initiating gasless withdrawal of {amount} {token} to {destination}...")

result = exchange.withdraw_from_bridge(
    destination=destination,
    token=token,
    amount=amount
)

# Display result
print("✅ Withdrawal submitted:")
print(result)
