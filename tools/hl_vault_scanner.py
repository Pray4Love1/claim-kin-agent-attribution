import requests


def check_purr_balances(address: str) -> None:
    url = "https://api.hyperliquid.xyz/info"
    payload = {"type": "spotBalance", "user": address}
    response = requests.post(url, json=payload).json()
    for token in response.get("balances", []):
        if token.get("coin", "").upper() == "PURR":
            print(f"✅ PURR for {address}: {token['amount']}")
            return
    print("❌ No PURR found.")


if __name__ == "__main__":
    target = input("Wallet: ")
    check_purr_balances(target)
