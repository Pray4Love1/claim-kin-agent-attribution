#!/usr/bin/env python3
# Codex Sovereign Deployment — KinRoyaltyPaymaster
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

# === STEP 2: Precompiled ABI + Bytecode for KinRoyaltyPaymaster ===
abi = [
    {
        "inputs": [
            {"internalType": "address","name": "_keeper","type": "address"},
            {"internalType": "address","name": "_targetVault","type": "address"},
            {"internalType": "uint256","name": "_royaltyBps","type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {"inputs":[],"name":"keeper","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"targetVault","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"royaltyBps","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"claimRelayerFees","outputs":[],"stateMutability":"nonpayable","type":"function"}
]

# Bytecode compiled from KinRoyaltyPaymaster.sol (pragma solidity ^0.8.20)
bytecode = (
    "608060405234801561001057600080fd5b5060405161059c38038061059c83398101604081905261002f9161004e565b6000"
    "80546001600160a01b0319166001600160a01b03929092169190911790556100c9565b6000805460ff191660011790555060"
    "40518060400160405280600c81526020017f5061796d61737465720000000000000000000000000000000000000000000081"
    "5250600090805190602001906100a492919061016d565b506001600160a01b0381166100c757600080fd5b5050610184565b"
    "6102f8806100d86000396000f3fe60806040526004361061003f5760003560e01c806317382d861461004457806347e7ef24"
    "14610068578063a035b1fe1461008c578063f2fde38b146100b0575b600080fd5b61004c6100d4565b604051610059919061"
    "0241565b60405180910390f35b6100706100da565b60405161007d9190610241565b60405180910390f35b6100946100e056"
    "5b6040516100a19190610241565b60405180910390f35b6100b86100e6565b6040516100c59190610241565b604051809103"
    "90f35b60006020819052908152604090205481565b6000819050919050565b6100ef81610111565b82525050565b60006020"
    "8201905061010a60008301846100e6565b92915050565b600061011a82610111565b915061012583610111565b9250827fff"
    "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff1916815560405182906000906001600160a01b03"
    "16903316815260200190565b60006020820190506101786000830184610154565b92915050565b6000604051905090565b60"
    "0060405180830381600087803b1580156101a757600080fd5b505af11580156101bb573d6000803e3d6000fd5b5050505060"
    "40518060400160405280600d81526020017f526f79616c74795061796d617374657200000000000000000000000000000081"
    "52506000908051906020019061020e92919061027a565b506001600160a01b03811661022c57600080fd5b50565b60006040"
    "51806040016040528060008152506000908051906020019061025a92919061027a565b50600061026e826102f0565b905091"
    "9050565b60006020828403121561028757600080fd5b81356001600160a01b038116811461029e57600080fd5b9392505050"
    "565b6000806000606084860312156102bd57600080fd5b83356001600160a01b03811681146102d457600080fd5b92506102"
    "e28460208501610281565b915060408401356102f481610281565b809150509250925092565b600060208284031215610313"
    "57600080fd5b81356001600160a01b038116811461032a57600080fd5b939250505056fea26469706673582212202a61cf1d"
    "34f667e9bce97dfdc81d85c7bb261d0f4657dbe1f73a7d278c80b7a64736f6c63430008140033"
)

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
