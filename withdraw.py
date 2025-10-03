import example_utils
from hyperliquid.utils import constants

def main():
    address, info, exchange = example_utils.setup(constants.MAINNET_API_URL, skip_ws=True)

    if exchange.account_address != exchange.wallet.address:
        raise Exception("Agents do not have permission to perform internal transfers")

    # Withdraw 1000 USDC to your external wallet
    withdraw_result = exchange.withdraw_from_bridge(
        asset="USDC",
        amount=1000,
        destination="0xYourETHWalletHere"
    )
    print(withdraw_result)

if __name__ == "__main__":
    main()
