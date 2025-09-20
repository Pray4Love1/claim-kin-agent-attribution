#!/usr/bin/env python3
"""
Codex Real Transaction Sender for Hyperliquid EVM

Sends real ETH from your Codex wallet to a recipient address on Hyperliquid chain.
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

print("✅ Codex wallet active")
print("📬 Address:", address)

# === Hyperliquid Chain Configuration ===
TO_ADDRESS = "0xE990E5E7Ce13DFCB97eA57181aEF594A8ca83779"  # Replace with your real target
AMOUNT_ETH = 0.001
CHAIN_ID = 1337
RPC_URL = "https://rpc.hyperliquid.xyz/evm"

# === Connect + Build TX ===
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise RuntimeError(f"❌ Web3 not connected to {RPC_URL}")

nonce = w3.eth.get_transaction_count(address)
gas_price = w3.eth.gas_price
value = w3.to_wei(AMOUNT_ETH, "ether")

tx = {
    "to": Web3.to_checksum_address(TO_ADDRESS),
    "value": value,
    "gas": 21000,
    "gasPrice": gas_price,
    "nonce": nonce,
    "chainId": CHAIN_ID
}

signed = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

print("🧾 Transaction sent!")
print("🔗 TX Hash:", tx_hash.hex())
print(f"💸 Sent {AMOUNT_ETH} ETH to {TO_ADDRESS} on Hyperliquid")
