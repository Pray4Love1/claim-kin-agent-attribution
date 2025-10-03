import sys, os

# Tell Python to use the local SDK folder, not the broken site-packages one
sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hyperliquid-api"))
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

from hyperliquid import Exchange
from hyperliquid.utils import constants

def setup(url=constants.MAINNET_API_URL, skip_ws=False):
    key_file_path = "env."  # or point to your key json
    with open(key_file_path, "r") as f:
        key = f.read().strip()
    exchange = Exchange(key, url, skip_ws=skip_ws)
    address = exchange.user().get("name")
    info = exchange.info()
    return address, info, exchange
