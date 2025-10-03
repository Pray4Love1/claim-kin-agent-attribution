import example_utils
from hyperliquid.utils import constants

def main():
    address, info, exchange = example_utils.setup(constants.MAINNET_API_URL, skip_ws=True)

    mainnet_HLP_vault = "0x31ca8395cf837de08b24da3f660e77761dfb974b"

    transfer_result = exchange.vault_usd_transfer(mainnet_HLP_vault, True, 5_000_000)
    print("✅ Transfer result:")
    print(transfer_result)

if __name__ == "__main__":
    main()
