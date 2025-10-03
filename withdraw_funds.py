# withdraw_funds.py
from web3 import Web3
from eth_account import Account
import os

w3 = Web3(Web3.HTTPProvider("https://rpc.hyperliquid.xyz/evm"))
acct = Account.from_key(os.getenv("PRIVATE_KEY"))

VAULT_ADDRESS = "0xYourVaultContractHere"
CORE_WRITER = "0x3333333333333333333333333333333333333333"
USDC = "0xYourUSDCAddressHere"
SHARES = 1_000_000  # replace with actual shares held (100% ownership)
EQUITY = 11_200_000 * (10**6)  # USDC has 6 decimals

# === Step 1: build action payload ===
from eth_abi import encode

action_type = b'\x00' * 31 + b'\x02'
encoded_args = encode(['address', 'uint256'], [VAULT_ADDRESS, EQUITY])
action = action_type + encoded_args

# === Step 2: build and send tx ===
abi = [{
  "name": "sendAction",
  "type": "function",
  "stateMutability": "nonpayable",
  "inputs": [{"name": "action", "type": "bytes"}],
  "outputs": []
}]

contract = w3.eth.contract(address=CORE_WRITER, abi=abi)
tx = contract.functions.sendAction(action).build_transaction({
  "chainId": 88888,
  "gas": 1000000,
  "gasPrice": w3.eth.gas_price,
  "nonce": w3.eth.get_transaction_count(acct.address),
})
signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

print("[✓] Withdraw action sent.")
print(f"TX: https://explorer.hyperliquid.xyz/tx/{tx_hash.hex()}")
