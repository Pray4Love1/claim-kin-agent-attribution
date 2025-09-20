#!/usr/bin/env python3
"""
Codex Test — Sign and Send from Codex Wallet

This script:
- Uses PRIVATE_KEY from environment (in-memory only)
- Signs a message for proof
- Sends a small transaction (to self)
- Requires codex_wallet_session.py to be run first
"""

import os
from web3 import Web3
from eth_account import Account

# === Load wallet from environment
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
if not PRIVATE_KEY:
    raise RuntimeError("❌ PRIVATE_KEY not found — run codex_wallet_session.py first.")

account = Account.from_key(PRIVATE_KEY)
address = account.address

print("✅ Codex wallet loaded")
print("📬 Address:", address)

# === Sign a message
message = "I am Keeper"
msg_hash = Web3.solidity_keccak(["string"], [message])
signed_msg = account.signHash(msg_hash)
print("✍️ Signed message 'I am Keeper':", signed_msg.signature.hex())

# === Send transaction (to self, for testing)
w3 = Web3(Web3.HTTPProvider("https://rpc.hyperliquid.xyz/evm"))

txn = {
    "to": address,
    "value": w3.to_wei(0.0001, "ether"),
    "gas": 21000,
    "gasPrice": w3.to_wei("1", "gwei"),
    "nonce": w3.eth.get_transaction_count(address),
    "chainId": 420  # ⚠️ Change this for Ethereum, Base, etc.
}

signed_tx = account.sign_transaction(txn)
tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

print("🧾 Sent transaction")
print("🔗 TX Hash:", tx_hash.hex())
