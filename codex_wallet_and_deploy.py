from web3 import Web3
from eth_account import Account

def connect_wallet(rpc_url):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise ConnectionError("Web3 not connected")
    return w3

def get_wallet_info(account: Account):
    # Assuming _private_key is intentionally accessed
    # You can refactor this later with secure wrappers
    return {
        "address": account.address,
        "private_key": account._private_key.hex()
    }
