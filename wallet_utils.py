import os
import json
from eth_account import Account

class LocalWallet:
    def __init__(self, label: str):
        self.wallet_dir = os.path.expanduser("~/.hyperliquid/wallets")
        self.label = label
        self.wallet_path = os.path.join(self.wallet_dir, f"{label}.json")
        if not os.path.exists(self.wallet_path):
            raise FileNotFoundError(f"Wallet '{label}' not found in {self.wallet_path}")
        with open(self.wallet_path, "r") as f:
            self.data = json.load(f)
        self.private_key = self.data["privateKey"]
        self.address = Account.from_key(self.private_key).address

    @staticmethod
    def create_new(label: str):
        acct = Account.create()
        wallet_dir = os.path.expanduser("~/.hyperliquid/wallets")
        os.makedirs(wallet_dir, exist_ok=True)
        path = os.path.join(wallet_dir, f"{label}.json")
        with open(path, "w") as f:
            json.dump({"privateKey": acct.key.hex()}, f)
        print(f"✅ New wallet '{label}' created at: {path}")
        return LocalWallet(label)
