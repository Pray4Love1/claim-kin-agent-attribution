import os
import getpass

priv_key = getpass.getpass("🔐 Enter your PRIVATE_KEY (hidden): ")
address = input("📬 Enter your ADDRESS (0x...): ")

os.environ["PRIVATE_KEY"] = priv_key
os.environ["ACCOUNT_ADDRESS"] = address

print("✅ Keys loaded into memory. Safe to run other scripts now.")
