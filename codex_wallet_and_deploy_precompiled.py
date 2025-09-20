from eth_account import Account

# Generate a new account (no mnemonic, random entropy)
acct = Account.create()

print("✅ New Wallet Generated:")
print(f"Private Key: {acct.key.hex()}")
print(f"Address:     {acct.address}")
