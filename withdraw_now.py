#!/usr/bin/env python3
"""Direct Codex withdrawal script (Keeper-only)."""

import os
from eth_account import Account
from web3 import Web3

# Config
RPC = "https://your-hyperliquid-rpc-here"  # replace with actual RPC URL
OWNER = "0x996994D2914DF4eEE6176FD5eE152e2922787EE7"

def main():
    secret = os.getenv("PRIVATE_KEY") or os.getenv("SECRET_KEY")
    if not secret:
        raise SystemExit("❌ No PRIVATE_KEY or SECRET_KEY in env")
    acct = Account.from_key(secret)

    w3 = Web3(Web3.HTTPProvider(RPC))

    # withdraw() selector
    selector = "0x3ccfd60b"

    tx = {
        "from": acct.address,
        "to": OWNER,  # vault contract address should go here if different
        "data": selector,
        "gas": 500000,
        "gasPrice": w3.eth.gas_price,
        "nonce": w3.eth.get_transaction_count(acct.address),
    }

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    print("✅ Withdrawal TX sent:", w3.to_hex(tx_hash))

if __name__ == "__main__":
    main()
