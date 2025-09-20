from hyperliquid.utils import constants
from hyperliquid.exchange import Exchange

def setup(url=constants.MAINNET_API_URL, skip_ws=False):
    key_file_path = "env."  # or point to your key json
    with open(key_file_path, "r") as f:
        key = f.read().strip()
    exchange = Exchange(key, url, skip_ws=skip_ws)
    address = exchange.user().get("name")
    info = exchange.info()
    return address, info, exchange
