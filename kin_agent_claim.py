from hyperliquid.info import Info
from hyperliquid.utils import constants

# Initialize connection to Hyperliquid Testnet API
info = Info(constants.TESTNET_API_URL, skip_ws=True)

# Target KinAgent wallet (f303 attribution vault)
wallet_address = "0xcd5051944f780a621ee62e39e493c489668acf4d"

# Query and print user state
user_state = info.user_state(wallet_address)
print("🛡️ KinLend Vault (f303) Attribution State:")
print(user_state)
