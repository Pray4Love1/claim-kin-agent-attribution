# filename: codex_send_withdrawal_tx.py

import os
import json
from web3 import Web3

# ENV VARS (set these in shell first)
PRIVATE_KEY = os.getenv("KIN_AGENT_KEY")
RPC = "https://base.blockpi.network/v1/rpc/public"  # or your preferred RPC

# Contract + data
CONTRACT = "0xe64a54E2533Fd126C2E452c5fAb544d80E2E4eb5"
CALLDATA = "0x3ccfd60b"

def main():
    if not PRIVATE_KEY:
        raise Exception("Set KIN_AGENT_KEY in your env")

    w3 = Web3(Web3.HTTPProvider(RPC))
    acct = w3.eth.account.from_key(PRIVATE_KEY)
    
    nonce = w3.eth.get_transaction_count(acct.address)
    gas_price = w3.eth.gas_price

    tx = {
        "to": Web3.to_checksum_address(CONTRACT),
        "data": CALLDATA,
        "nonce": nonce,
        "gas": 120000,  # adjust if needed
        "gasPrice": gas_price,
        "chainId": 8453,  # BASE mainnet
        "value": 0
    }

    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print("✅ TX sent:", tx_hash.hex())

if __name__ == "__main__":
    main()
