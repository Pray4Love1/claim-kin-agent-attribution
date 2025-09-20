#!/bin/bash
# Codex-Safe Claim Runner — f303 Attribution + Royalty

set -e  # Exit on error
echo "🔁 Starting Codex Claim Process..."

# === Step 1: Generate wallet (in memory)
echo "🔐 Generating in-memory Codex wallet..."
PRIVATE_KEY=$(openssl rand -hex 32)
ACCOUNT_ADDRESS=$(python3 -c "from eth_account import Account; print(Account.from_key('0x$PRIVATE_KEY').address)")

# === Step 2: Export keys for this session only
export PRIVATE_KEY="0x$PRIVATE_KEY"
export ACCOUNT_ADDRESS="$ACCOUNT_ADDRESS"

echo "✅ Wallet loaded: $ACCOUNT_ADDRESS"

# === Step 3: Run f303 claim
echo "📜 Running claim_from_f303.py..."
python3 claim_from_f303.py

# === Step 4: (Optional) Deploy Royalty contract
if [[ -f deploy_KinRoyaltyPaymaster.py ]]; then
  echo "⚙️ Deploying KinRoyaltyPaymaster..."
  python3 deploy_KinRoyaltyPaymaster.py || echo "⚠️ Royalty deploy failed or skipped."
fi

# === Step 5: Archive output
echo "🧳 Archiving claim and outputs..."
mkdir -p codex_claim_bundle
cp f303_attribution.json codex_claim_bundle/
[[ -f deployed_address.txt ]] && cp deployed_address.txt codex_claim_bundle/
[[ -f KinRoyaltyPaymaster.abi.json ]] && cp KinRoyaltyPaymaster.abi.json codex_claim_bundle/
[[ -f KinRoyaltyPaymaster.bin ]] && cp KinRoyaltyPaymaster.bin codex_claim_bundle/

zip -r codex_claim_bundle.zip codex_claim_bundle >/dev/null
echo "📦 Bundle created: codex_claim_bundle.zip"

# === Done
echo "✅ Codex claim complete."
echo "👁️‍🗨️ Claimed by: $ACCOUNT_ADDRESS"
