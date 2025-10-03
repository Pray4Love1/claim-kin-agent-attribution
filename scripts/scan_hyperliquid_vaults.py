#!/usr/bin/env python3
"""Scan Hyperliquid vault bytecode for known KinVault selectors."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RPC_URL = "https://rpc.hyperliquid.xyz/evm"
OUTPUT_PATH = Path("proof/hyperliquid/hl_contract_matches.json")

# Addresses that have been referenced throughout the attribution proofs.
VAULT_ADDRESSES: List[str] = [
    "0xdfC24b077bC1425Ad1DeA75BCB6F8158E10Df303",
    "0x996994D2914DF4eEE6176FD5eE152e2922787EE7",
    "0xcd5051944f780a621ee62e39e493c489668acf4d",
]

# Canonical KinVault / SolaraKin authored function signatures we are seeking.
FUNCTION_SIGNATURES: List[str] = [
    "deposit(address,uint256)",
    "withdraw(uint256,address,address)",
    "balanceOf(address)",
    "claimKinVault(address,uint256)",
    "claimRoyalties()",
    "submitProof(bytes32)",
]


ROUND_CONSTANTS = [
    0x0000000000000001,
    0x0000000000008082,
    0x800000000000808A,
    0x8000000080008000,
    0x000000000000808B,
    0x0000000080000001,
    0x8000000080008081,
    0x8000000000008009,
    0x000000000000008A,
    0x0000000000000088,
    0x0000000080008009,
    0x000000008000000A,
    0x000000008000808B,
    0x800000000000008B,
    0x8000000000008089,
    0x8000000000008003,
    0x8000000000008002,
    0x8000000000000080,
    0x000000000000800A,
    0x800000008000000A,
    0x8000000080008081,
    0x8000000000008080,
    0x0000000080000001,
    0x8000000080008008,
]

RHO_OFFSETS = (
    (0, 36, 3, 41, 18),
    (1, 44, 10, 45, 2),
    (62, 6, 43, 15, 61),
    (28, 55, 25, 21, 56),
    (27, 20, 39, 8, 14),
)


def _rotl64(value: int, shift: int) -> int:
    return ((value << shift) & 0xFFFFFFFFFFFFFFFF) | (value >> (64 - shift))


def _keccak_f(state: List[int]) -> None:
    for rc in ROUND_CONSTANTS:
        c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rotl64(c[(x + 1) % 5], 1) for x in range(5)]
        for index in range(25):
            state[index] ^= d[index % 5]

        b = [0] * 25
        for x in range(5):
            for y in range(5):
                idx = x + 5 * y
                new_x = y
                new_y = (2 * x + 3 * y) % 5
                b[new_x + 5 * new_y] = _rotl64(state[idx], RHO_OFFSETS[x][y])

        for x in range(5):
            for y in range(5):
                idx = x + 5 * y
                state[idx] = b[idx] ^ ((~b[(x + 1) % 5 + 5 * y]) & b[(x + 2) % 5 + 5 * y])

        state[0] ^= rc


def keccak256(data: bytes) -> bytes:
    rate_bytes = 136
    state = [0] * 25
    block_size = len(data)
    offset = 0
    while offset + rate_bytes <= block_size:
        block = data[offset : offset + rate_bytes]
        for i in range(0, rate_bytes, 8):
            state[i // 8] ^= int.from_bytes(block[i : i + 8], "little")
        _keccak_f(state)
        offset += rate_bytes

    remainder = bytearray(data[offset:])
    remainder.append(0x01)
    while len(remainder) < rate_bytes:
        remainder.append(0x00)
    remainder[-1] ^= 0x80

    for i in range(0, rate_bytes, 8):
        chunk = remainder[i : i + 8]
        state[i // 8] ^= int.from_bytes(chunk, "little")
    _keccak_f(state)

    output = bytearray()
    while len(output) < 32:
        for word in state[: rate_bytes // 8]:
            output.extend(word.to_bytes(8, "little"))
            if len(output) >= 32:
                break
        if len(output) >= 32:
            break
        _keccak_f(state)
    return bytes(output[:32])


def signature_to_selector(signature: str) -> str:
    """Return the 4-byte selector for a function signature as 0x-prefixed hex."""

    digest = keccak256(signature.encode())
    return digest[:4].hex()


def fetch_bytecode(address: str) -> str:
    """Fetch deployed bytecode for an address from the Hyperliquid RPC."""

    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "eth_getCode",
            "params": [address, "latest"],
            "id": 1,
        }
    ).encode()
    request = Request(RPC_URL, data=payload, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=20) as response:  # nosec B310 - trusted RPC endpoint
        body = json.load(response)
    return body.get("result", "")


def scan_address(address: str, selectors: Dict[str, str]) -> Dict[str, Iterable[str]]:
    """Return the subset of signatures that appear in the contract bytecode."""

    bytecode = fetch_bytecode(address).lower()
    matches = [signature for signature, selector in selectors.items() if selector in bytecode]
    return {"selectors": matches}


def main() -> int:
    selectors = {signature: signature_to_selector(signature) for signature in FUNCTION_SIGNATURES}

    results: Dict[str, Dict[str, Iterable[str]]] = {}
    for address in VAULT_ADDRESSES:
        try:
            match_info = scan_address(address, selectors)
        except (HTTPError, URLError, TimeoutError) as exc:  # pragma: no cover - network failure path
            print(f"⚠️  Failed to scan {address}: {exc}", file=sys.stderr)
            match_info = {"error": str(exc), "selectors": []}
        results[address] = match_info

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2) + "\n")
    print(f"Wrote results to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
