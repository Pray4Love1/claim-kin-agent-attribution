import os, json
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct
from claims.vault_scanner_utils import claim_digest

# Load .env if it exists
load_dotenv()

PRIVATE_KEY = (
    os.getenv("KIN_AGENT_KEY")
    or os.getenv("SECRET_KEY")
    or os.getenv("PRIVATE_KEY")
)

# If not found, try config.json
if not PRIVATE_KEY and os.path.exists("config.json"):
    with open("config.json") as f:
        cfg = json.load(f)
        PRIVATE_KEY = cfg.get("KIN_AGENT_KEY") or cfg.get("SECRET_KEY") or cfg.get("PRIVATE_KEY")

if not PRIVATE_KEY:
    raise RuntimeError("❌ No private key found in env or config.json")

# Example vault claim info
user = "0x1111111111111111111111111111111111111111"
vault_id = "0x" + "aa" * 32
attribution = "0x" + "bb" * 32
balance = 42

digest = claim_digest(user, vault_id, balance, attribution)

acct = Account.from_key(PRIVATE_KEY)
msg = encode_defunct(hexstr=digest.hex())
signed = acct.sign_message(msg)

claim_payload = {
    "user": user,
    "vaultId": vault_id,
    "balance": str(balance),
    "attribution": attribution,
    "signature": signed.signature.hex(),
    "signer": acct.address,
}

print("✅ Claim digest:", digest.hex())
print("✅ Signature:", signed.signature.hex())
print("✅ Signer:", acct.address)
print("\n--- JSON Payload ---")
print(json.dumps(claim_payload, indent=2))
