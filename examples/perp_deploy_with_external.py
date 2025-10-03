import example_utils
from hyperliquid.utils import constants

# === CONFIG ===
TOKEN_NAME = "KIN"
ORACLE_PRICE = 1.618  # Set your external oracle price here
EXPIRY = 0  # Perpetual

def main():
    # Setup wallet + exchange
    address, info, exchange = example_utils.setup(constants.MAINNET_API_URL, skip_ws=True)
    print(f"🧠 Deploying from address: {address}")

    # Set external oracle price
    external_price = {
        TOKEN_NAME: ORACLE_PRICE
    }
    print(f"🔧 Setting external oracle price for {TOKEN_NAME} = {ORACLE_PRICE}")
    result = exchange.perp_deploy_set_oracle(TOKEN_NAME, external_price)
    print("✅ Oracle price set:", result)

    # Deploy the perpetual market
    print(f"🚀 Deploying perpetual for {TOKEN_NAME}...")
    deploy_result = exchange.perp_deploy(
        {
            "name": TOKEN_NAME,
            "szDecimals": 6,
            "weiDecimals": 18,
            "perpExpiry": EXPIRY
        }
    )
    print("✅ Perpetual deploy result:", deploy_result)

if __name__ == "__main__":
    main()
