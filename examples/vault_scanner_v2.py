"""Utilities for inspecting the VaultScannerV2WithSig deployment package."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from claims.vault_scanner_utils import (
    PACKAGE_PATH,
    claim_digest,
    claim_message_hash,
    describe_functions,
    load_package,
)

EXAMPLE_USER = "0x1111111111111111111111111111111111111111"
EXAMPLE_VAULT_ID = "0x" + "22" * 32
EXAMPLE_ATTRIBUTION = "0x" + "33" * 32
EXAMPLE_BALANCE = 42


def _coerce_abi(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    entries: List[Dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            entries.append(item)
    return entries


def main() -> None:
    package: Dict[str, Any] = load_package()
    abi = _coerce_abi(package.get("abi"))
    bytecode = package.get("bytecode", "")
    print(f"Loaded VaultScannerV2WithSig package from {PACKAGE_PATH}.")
    print(f"ABI entries: {len(abi)}")
    print(f"Bytecode length: {len(bytecode)} hex characters")
    if not bytecode or bytecode in {"0x", "0X"}:
        print("⚠️  Deployment bytecode is a placeholder. Compile VaultScannerV2WithSig to populate this field.")

    print("\nFunctions:")
    for description in describe_functions(abi):
        print(f"  • {description}")

    digest = claim_digest(EXAMPLE_USER, EXAMPLE_VAULT_ID, EXAMPLE_BALANCE, EXAMPLE_ATTRIBUTION)
    final_hash = claim_message_hash(EXAMPLE_USER, EXAMPLE_VAULT_ID, EXAMPLE_BALANCE, EXAMPLE_ATTRIBUTION)

    print("\nSample keeper signing inputs:")
    print(f"  • claimDigest         = 0x{digest.hex()}")
    print(f"  • ethSignedMessage    = 0x{final_hash.hex()}")


if __name__ == "__main__":
    main()