# Example script for deploying a perp dex with externalPerpPxs support (v0.19.0+)

import example_utils
from hyperliquid.utils import constants

# Toggle this to True if you're registering a new DEX
REGISTER_PERP_DEX = True

DUMMY_DEX = "test"

def main():
    # Setup: get wallet address, info, and exchange client
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL)

    # Step 0: Check auction/gas info
    perp_deploy_auction_status = info.query_perp_deploy_auction_status()
    print("⏱️ Perp deploy auction status:", perp_deploy_auction_status)

    # Step 1: Optionally Register DEX + Asset
    perp_dex_schema_input = None
    if REGISTER_PERP_DEX:
        perp_dex_schema_input = {
            "fullName": "test dex",
            "collateralToken": 0,
            "oracleUpdater": address,
        }

    register_asset_result = exchange.perp_deploy_register_asset(
        dex=DUMMY_DEX,
        max_gas=1000000000000,  # 1k HYPE
        coin=f"{DUMMY_DEX}:TEST0",
        sz_decimals=2,
        oracle_px="10.0",
        margin_table_id=10,
        only_isolated=False,
        schema=perp_dex_schema_input,
    )
    print("✅ Asset registration result:", register_asset_result)

    # Step 2: Set Oracle Prices (includes externalPerpPxs from v0.19.0)
    set_oracle_result = exchange.perp_deploy_set_oracle(
        dex=DUMMY_DEX,
        oracle_pxs={
            f"{DUMMY_DEX}:TEST0": "12.0",
            f"{DUMMY_DEX}:TEST1": "1.0",
        },
        all_mark_pxs=[
            {
                f"{DUMMY_DEX}:TEST0": "14.0",
                f"{DUMMY_DEX}:TEST1": "3.0",
            }
        ],
        external_perp_pxs={
            f"{DUMMY_DEX}:TEST0": "12.1",
            f"{DUMMY_DEX}:TEST1": "1.1",
        },
    )
    print("✅ Set oracle result:", set_oracle_result)

    # Step 3: View DEX Meta
    print("📦 DEX Meta:", info.meta(dex=DUMMY_DEX))


if __name__ == "__main__":
    main()
