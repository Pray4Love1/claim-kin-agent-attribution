#!/usr/bin/env python3
# Codex Sovereign Wallet + KinRoyalty Deployment
# Keeper Authorship: CT 2025-09-14

import os

from eth_account import Account
from solcx import compile_source
from web3 import Web3

# === STEP 1: Generate sovereign wallet ===
priv_key_bytes = os.urandom(32)
acct = Account.from_key(priv_key_bytes)

print("Private Key (KEEP OFFLINE):", acct.key.hex())
print("Public Address:", acct.address)

# === STEP 2: Solidity source for KinRoyalty ===
kinroyalty_source = """
// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

interface IVault {
    function deposit(uint256 amount) external;
    function withdraw(uint256 amount) external;
}

contract KinRoyalty {
    address public immutable keeper;
    address public immutable targetVault;
    uint256 public immutable royaltyBps;

    constructor(address _keeper, address _targetVault, uint256 _royaltyBps) {
        require(_royaltyBps <= 10000, "Invalid royalty");
        keeper = _keeper;
        targetVault = _targetVault;
        royaltyBps = _royaltyBps;
    }

    receive() external payable {}
}
"""

# === STEP 3: Compile contract ===
compiled_sol = compile_source(kinroyalty_source, output_values=["abi", "bin"])
contract_id, contract_interface = compiled_sol.popitem()

abi = contract_interface["abi"]
bytecode = contract_interface["bin"]

# === STEP 4: Connect to chain ===
# Replace with correct RPC endpoint (offline-safe once synced)
rpc_url = "https://mainnet.infura.io/v3/YOUR_INFURA_KEY"
w3 = Web3(Web3.HTTPProvider(rpc_url))
assert w3.is_connected(), "Web3 not connected"

# === STEP 5: Deploy contract ===
KinRoyalty = w3.eth.contract(abi=abi, bytecode=bytecode)

keeper_address = acct.address
target_vault = "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303"  # Hyperliquid f303 vault
royalty_bps = 1100  # 11%

construct_txn = KinRoyalty.constructor(
    keeper_address,
    target_vault,
    royalty_bps
).build_transaction({
    "from": acct.address,
    "nonce": w3.eth.get_transaction_count(acct.address),
    "gas": 500000,
    "gasPrice": w3.to_wei("25", "gwei"),
})

signed = w3.eth.account.sign_transaction(construct_txn, private_key=acct.key)
tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

print("Deployment sent. TX hash:", tx_hash.hex())
print("Await confirmation with: w3.eth.wait_for_transaction_receipt(tx_hash)")
