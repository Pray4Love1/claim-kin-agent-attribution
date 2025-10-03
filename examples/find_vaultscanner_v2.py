#!/usr/bin/env python3
"""Scan candidate vault addresses for VaultScannerV2WithSig bytecode markers on mainnet."""

from __future__ import annotations

import json
import sys
from typing import Dict, List, Sequence, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

from claims.vault_scanner_utils import (
    describe_functions,
    function_selectors,
    load_package,
)

RPC_URL = "https://rpc.hyperliquid.xyz/evm"

# Known vaults observed in other attribution scripts. More can be supplied on the
# command line.
DEFAULT_VAULTS = [
    "0xdfC24b077bC1425Ad1DeA75BCB6F8158E10Df303",
    "0x996994D2914DF4eEE6176FD5eE152e2922787EE7",
    "0xcd5051944f780a621ee62e39e493c489668acf4d",
]


def fetch_bytecode(address: str) -> str:
    """Fetch deployed bytecode from the Hyperliquid mainnet RPC."""

    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "eth_getCode",
            "params": [address, "latest"],
            "id": 1,
        }
    ).encode("utf-8")
    request = Request(
        RPC_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        body = response.read()
    payload_dict = json.loads(body.decode("utf-8"))
    return str(payload_dict.get("result", "") or "")


def scan_vault(bytecode: str, selector_map: Dict[str, str]) -> List[Tuple[str, str]]:
    """Return matching (signature, selector) pairs found in the bytecode."""

    lowered = bytecode.lower()
    matches: List[Tuple[str, str]] = []
    for signature, selector in selector_map.items():
        if selector.lower() in lowered:
            matches.append((signature, selector))
    return matches


def main(addresses: Sequence[str]) -> int:
    package = load_package()
    abi = package.get("abi", [])
    selector_map = function_selectors(abi)
    descriptions = describe_functions(abi)

    print("VaultScannerV2WithSig ABI functions loaded:")
    for description in descriptions:
        print(f"  • {description}")

    print("\n🔍 Scanning bytecode for VaultScannerV2 selectors...\n")

    exit_code = 0
    for address in addresses:
        try:
            bytecode = fetch_bytecode(address)
        except URLError as exc:  # pragma: no cover - network failure handling
            print(f"Vault {address}: ⚠️ RPC error - {exc}")
            exit_code = 1
            continue

        matches = scan_vault(bytecode, selector_map)
        if matches:
            print(f"Vault {address}: ✅ matches found")
            for signature, selector in matches:
                print(f"  • {signature} → {selector}")
        else:
            print(f"Vault {address}: ❌ no VaultScannerV2 selectors detected")
        print()

    return exit_code


if __name__ == "__main__":
    args = sys.argv[1:] or DEFAULT_VAULTS
    sys.exit(main(args))