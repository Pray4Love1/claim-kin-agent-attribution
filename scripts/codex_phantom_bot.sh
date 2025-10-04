#!/bin/bash
set -e

# === Codex Setup Script for Phantom Bot ===
# Executed at container creation (setup phase)
# Network access is ENABLED during this phase

echo "🔧 Installing Python + JS dependencies..."

# 1. Python requirements
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

# 2. Node.js (optional)
if [ -f package.json ]; then
  npm install
fi

# 3. Go support (optional)
if [ -f go.mod ]; then
  go mod tidy
fi

# 4. Optional Codex Phantom environment file generator
cat <<EOF > codex_phantom.env
# Phantom Bot Environment Template
HL_API_URL=https://api.hyperliquid.xyz
PRIVATE_KEY=$PRIVATE_KEY
VAULT_ADDRESS=
EOF

echo "✅ Phantom environment initialized"
