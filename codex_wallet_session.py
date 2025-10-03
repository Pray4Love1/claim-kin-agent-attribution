#!/usr/bin/env python3
"""
Codex Wallet Session Loader — securely loads PRIVATE_KEY + ACCOUNT_ADDRESS,
prints wallet summary, and injects into os.environ for in-script use.
"""

import os
from getpass import getpass
from eth_account import Account

def main():
    print("🔐 Codex Wallet Session — Start")
    
    # Prompt for private key safely
    priv_key = getpass("Enter your PRIVATE_KEY (hidden input): ").strip()
    if not priv_key.startswith("0x"):
        priv_key = "0x" + priv_key

    try:
        acct = Account.from_key(priv_key)
    except Exception as e:
        print("❌ Invalid private key:", str(e))
        return

    address = acct.address

    # Set for session
    os.environ["PRIVATE_KEY"] = priv_key
    os.environ["ACCOUNT_ADDRESS"] = address

    # Optional print
    print("✅ Codex wallet loaded")
    print("📬 Address:", address)
    print("🔑 Key is active in-memory only (not saved)")

    # Useable example: signing
    print("\n💡 Example: sign a message")
    msg = "I am Keeper"
    sig = acct.sign_message(Account.signable_message(text=msg))
    print("✍️ Signature:", sig.signature.hex())

if __name__ == "__main__":
    main()
