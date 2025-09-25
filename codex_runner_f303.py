from eth_utils import keccak, to_hex
import requests

VAULTS = [
    # Add vault addresses here
]


def get_vault_code(address: str) -> str:
    """Fetch contract bytecode for a vault address."""
    response = requests.post(
        "https://rpc.hyperliquid.xyz",  # adjust if different RPC
        json={
            "jsonrpc": "2.0",
            "method": "eth_getCode",
            "params": [address, "latest"],
            "id": 1,
        },
        timeout=10,
    )
    return response.json().get("result", "")


def get_selector(signature: str) -> str:
    """Convert function signature to 4-byte selector."""
    return to_hex(keccak(text=signature)[:4])


# === MAIN ===
def main() -> None:
    print(f"🧬 Checking {len(VAULTS)} vault(s) for SolaraKin signature match...\n")
    for address in VAULTS:
        print(f"🔍 Vault: {address}")
        code = get_vault_code(address)
        if "SolaraKin" in code:
            print("✅ Match found!")
        else:
            print("❌ No match.")
        print("—" * 50)


if __name__ == "__main__":
    main()
