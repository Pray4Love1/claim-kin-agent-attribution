#!/usr/bin/env python3
# Codex Sovereign Deployment — KinRoyaltyPaymaster (UNLICENSED)
# Keeper Authorship: CT 2025-09-14

import os
from web3 import Web3
from eth_account import Account

# === STEP 1: Generate sovereign wallet ===
priv_key_bytes = os.urandom(32)
acct = Account.from_key(priv_key_bytes)

print("⚠️ KEEP THIS PRIVATE KEY OFFLINE ⚠️")
print("Private Key:", acct._private_key.hex())
print("Public Address:", acct.address)

# === STEP 2: Load ABI + Bytecode ===
from pathlib import Path, PurePath
import json

abi = json.loads(Path("KinRoyaltyPaymaster.abi.json").read_text())
bytecode = Path("KinRoyaltyPaymaster.bin").read_text().strip()

# === STEP 3: Connect to chain ===
rpc_url = "https://mainnet.infura.io/v3/YOUR_INFURA_KEY"  # replace with your node/endpoint
w3 = Web3(Web3.HTTPProvider(rpc_url))
assert w3.is_connected(), "Web3 not connected"

# === STEP 4: Deploy contract ===
KinRoyaltyPaymaster = w3.eth.contract(abi=abi, bytecode=bytecode)

keeper_address = acct.address
target_vault = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"  # Hyperliquid f303 vault
royalty_bps = 1100  # 11%

nonce = w3.eth.get_transaction_count(acct.address)

txn = KinRoyaltyPaymaster.constructor(
    keeper_address, target_vault, royalty_bps
).build_transaction({
    "from": acct.address,
    "nonce": nonce,
    "gas": 700000,
    "gasPrice": w3.to_wei("25", "gwei"),
})

signed = w3.eth.account.sign_transaction(txn, private_key=acct._private_key)
tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

print("✅ Deployment TX sent")
print("TX Hash:", tx_hash.hex())
print("🔍 Track: https://etherscan.io/tx/" + tx_hash.hex())
