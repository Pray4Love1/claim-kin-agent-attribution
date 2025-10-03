import os
import json
from eth_account import Account
from web3 import Web3
from eth_abi import encode

RPC_URL = "https://rpc.hyperliquid.xyz/evm"
CLAIM_FILE = "claims/royalty_claim_hyperliquid.json"
CORE_WRITER = "0x3333333333333333333333333333333333333333"

PRIVATE_KEY = os.getenv("KIN_AGENT_KEY")
if not PRIVATE_KEY:
    raise SystemExit("❌ Please set your KIN_AGENT_KEY environment variable.")

acct = Account.from_key(PRIVATE_KEY)
w3 = Web3(Web3.HTTPProvider(RPC_URL))

with open(CLAIM_FILE, "r") as f:
    claim = json.load(f)

vault_address = claim["vault"]
amount_usd = float(claim["amount_usd"])
amount_wei = int(amount_usd * 1_000_000)  # USDC = 6 decimals

print(f"[📂] Claim: {amount_usd} USD from vault {vault_address}")

action_type = b'\x00' * 31 + b'\x02'
encoded = encode(["address", "uint256"], [vault_address, amount_wei])
action_bytes = action_type + encoded

abi = [{
    "name": "sendAction",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [{"name": "action", "type": "bytes"}],
    "outputs": []
}]

contract = w3.eth.contract(address=CORE_WRITER, abi=abi)
tx = contract.functions.sendAction(action_bytes).build_transaction({
    "chainId": 88888,
    "gas": 350000,
    "gasPrice": w3.eth.gas_price,
    "nonce": w3.eth.get_transaction_count(acct.address),
})

signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

print(f"[🚀] Withdrawal broadcasted: {tx_hash.hex()}")
print(f"[🔗] Explorer: https://explorer.hyperliquid.xyz/tx/{tx_hash.hex()}")
