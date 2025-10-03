# hyperliquid/exchange_module.py

import os
import json
from hyperliquid.info import Info

class Exchange:
    def __init__(self, key=None, url=None):
        self.key = key or os.getenv("HL_KEY")
        self.url = url or os.getenv("MAINNET_API_URL")

    def connect(self):
        print(f"[Exchange] Connected to {self.url} using key: {self.key}")
