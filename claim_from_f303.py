import example_utils
from hyperliquid.utils import constants

def main():
    address, info, exchange = example_utils.setup(constants.MAINNET_API_URL)
    f303_vault = "0x31ca8395cf837de08b24da3f660e77761dfb974b"
    result = exchange.vault_usd_transfer(f303_vault, True, 1_000_000)
    print(f"✅ Claimed to F303 vault: {result}")

if __name__ == "__main__":
    main()
