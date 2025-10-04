import os
from web3 import Web3
from eth_account import Account

RPC_URL = os.getenv("RPC_URL")            # e.g. https://mainnet.infura.io/v3/YOUR_KEY
PRIVATE_KEY = os.getenv("PRIVATE_KEY")    # set in GitHub/Container secret
DESTINATION = os.getenv("DESTINATION")    # the wallet you want to send to

if not RPC_URL or not PRIVATE_KEY or not DESTINATION:
    raise RuntimeError("Missing RPC_URL, PRIVATE_KEY, or DESTINATION env vars")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = Account.from_key(PRIVATE_KEY)
wallet = acct.address

print(f"🔑 Loaded wallet {wallet}")
balance = w3.eth.get_balance(wallet)
print(f"💰 Balance: {w3.from_wei(balance, 'ether')} ETH")

# Gas setup
gas_price = w3.eth.gas_price
gas_limit = 21000
amount_to_send = balance - gas_price * gas_limit
if amount_to_send <= 0:
    raise RuntimeError("Not enough balance to cover gas")

tx = {
    "from": wallet,
    "to": DESTINATION,
    "value": amount_to_send,
    "gas": gas_limit,
    "gasPrice": gas_price,
    "nonce": w3.eth.get_transaction_count(wallet),
    "chainId": w3.eth.chain_id,
}

signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
print(f"🚀 TX sent! Hash: {tx_hash.hex()}")
