#!/usr/bin/env python3
# Codex: Withdraw from Hyperliquid HLP Vault
# Vault: 0xdfC24b077bC1425Ad1DeA75BCB6F8158E10Df303
# Keeper: 0x996994D2914DF4eEE6176FD5eE152e2922787EE7
# CT: 2025-09-17T03:35 AM

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
import os

# === RPC ===
RPC_URL = "https://rpc.hyperliquid.xyz/evm"
VAULT_ADDRESS = "0xdfC24b077bC1425Ad1DeA75BCB6F8158E10Df303"
KEEPER_ADDRESS = "0x996994D2914DF4eEE6176FD5eE152e2922787EE7"

# === Load Wallet ===
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
if not PRIVATE_KEY:
    raise Exception("❌ PRIVATE_KEY not set in environment.")
acct = Account.from_key(PRIVATE_KEY)

# === Connect ===
w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# === Vault ABI (minimal for withdraw) ===
abi = [
    {
        "inputs": [{"internalType": "uint256", "name": "shares", "type": "uint256"}],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "assets", "type": "uint256"}],
        "name": "redeem",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

contract = w3.eth.contract(address=VAULT_ADDRESS, abi=abi)

# === Choose withdraw method ===
# NOTE: You must specify how much you want to withdraw (in shares or assets).
# Example: withdraw all shares (replace 1000 with actual share balance).
shares_to_withdraw = 100000000

tx = contract.functions.withdraw(shares_to_withdraw).build_transaction({
    "from": acct.address,
    "nonce": w3.eth.get_transaction_count(acct.address),
    "gas": 750000,
    "maxFeePerGas": w3.to_wei("2.5", "gwei"),
    "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
    "chainId": w3.eth.chain_id
})

signed_tx = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

print("✅ Withdraw sent to HLP vault.")
print("🔗 TX Hash:", tx_hash.hex())
