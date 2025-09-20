import { PrivateKeyAccount, Wallet } from "ethers";
import { WalletSigner } from "hyperliquid-js";
import { OrderBookClient, constants } from "hyperliquid-js";

const PRIVATE_KEY = process.env.KIN_F303_KEY!;
const ADDRESS = ""0x2DFae61AdB033eD13F4F44825A25979adD0cbD37";

async function runClaim() {
  const signer = new Wallet(PRIVATE_KEY);
  const client = new OrderBookClient(constants.TESTNET_API_URL, signer);

  // Claim attribution by placing a non-funded position
  const result = await client.placeOrder({
    coin: "BTC",
    isBuy: true,
    sz: "0.001",
    limitPx: "10000", // way below market
    orderType: "limit",
    reduceOnly: false,
    cloid: "f303-claim",
  });

  console.log("✅ Attribution claim submitted from f303:");
  console.log(result);
}

runClaim().catch((e) => {
  console.error("❌ Failed to claim attribution from f303:", e);
});
