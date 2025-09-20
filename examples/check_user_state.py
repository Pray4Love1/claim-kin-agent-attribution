# examples/check_user_state.py

from hyperliquid.utils import constants
import example_utils


def main():
    # Initializes address, Info, and Exchange using your config.json data
    address, info, _ = example_utils.setup(constants.MAINNET_API_URL, skip_ws=True)

    # Fetch and display user balances and margin summary
    user_state = info.user_state(address)
    spot_user_state = info.spot_user_state(address)
    print("Perp user state:", user_state)
    print("Spot user state:", spot_user_state)


if __name__ == "__main__":
    main()
