#!/usr/bin/env python3
"""Codex wallet and deploy helper — precompiled and bound for Keeper use only."""

import os
from eth_account import Account
from web3 import Web3


def get_wallet() -> Account:
    secret = os.getenv("PRIVATE_KEY") or os.getenv("SECRET_KEY")
    if not secret:
        raise SystemExit("❌ No PRIVATE_KEY or SECRET_KEY provided.")
    return Account.from_key(secret)


def deploy_precompiled(w3: Web3, bytecode: str) -> str:
    acct = get_wallet()
    tx = {
        "from": acct.address,
        "data": bytecode,
        "gas": 5_000_000,
        "gasPrice": w3.eth.gas_price,
        "nonce": w3.eth.get_transaction_count(acct.address),
    }
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return w3.to_hex(tx_hash)
