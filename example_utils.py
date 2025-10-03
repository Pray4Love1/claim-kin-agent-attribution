import os
from hyperliquid import example_utils
from hyperliquid.utils.constants import MAINNET_API_URL

# Load private key from environment variable for security
# Set in .env file: secret_key=your_private_key_here
# Example: echo "secret_key=0xYourPrivateKey" > .env
private_key = os.getenv("secret_key")
if not private_key:
    raise ValueError("Please set secret_key in your environment variables")

# Initialize the SDK for mainnet
network = "mainnet"
exchange = example_utils.setup(
    network=network,
    private_key=private_key,
    # Optional: Add wallet address if required by SDK
    # wallet_address="0x75E5522192b8FB1ed237dAc5eFDBab452bCE12fb"
)

# Define transfer parameters
destination_address = ""  # HyperLiquid/Arbitrum address
source_dex = "hyperliquid"  # Internal HyperLiquid transfer
destination_dex = "hyperliquid"  # Internal transfer; use "arbitrum" for external
token = "USDC"  # HyperLiquid supports USDC
amount = "1.23"  # Transfer 1.23 USDC (6 decimals: 1,230,000 wei)

# Perform the asset transfer
try:
    response = exchange.send_asset(
        destination_address=destination_address,
        source_dex="arbitrum",
        destination_dex=destination_dex,
        token=token,
        amount=amount
    )
    print(f"Transfer response: {response}")
except Exception as e:
    print(f"Error during transfer: {str(e)}")

# Verify transaction on-chain
if response.get("tx_hash"):
    print(f"Check transaction at: https://explorer.hyperliquid.xyz/tx/{response['tx_hash']} (mainnet)")
