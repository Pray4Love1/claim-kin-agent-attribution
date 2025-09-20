import requests
import json

url = "https://api.hyperliquid.xyz/info"

payload = {
    "type": "metaAndAssetCtxs"
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    result = response.json()
    print("✅ Tradable Assets & Market Context:")
    print(json.dumps(result, indent=2))
else:
    print(f"❌ Request Failed: {response.status_code}")
    print(response.text)
