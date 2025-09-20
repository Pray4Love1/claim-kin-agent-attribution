#!/usr/bin/env python3
# Codex: Sovereign Vault Scanner — SolaraKin Signature Mapper
# CT: 2025-09-17T06:26 (Central Time)

import requests
import json
from eth_utils import keccak, to_hex
import urllib.error
import urllib.request

# === LIGHTWEIGHT CRYPTO PRIMITIVES ===

MASK_64 = (1 << 64) - 1
ROTATION_OFFSETS = (
    (0, 36, 3, 41, 18),
    (1, 44, 10, 45, 2),
    (62, 6, 43, 15, 61),
    (28, 55, 25, 21, 56),
    (27, 20, 39, 8, 14),
)

ROUND_CONSTANTS = (
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
)

def _rotl64(value: int, shift: int) -> int:
    return ((value << shift) | (value >> (64 - shift))) & MASK_64

def _keccak_f(state: list[int]) -> None:
    for rc in ROUND_CONSTANTS:
        c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rotl64(c[(x + 1) % 5], 1) for x in range(5)]

        for x in range(5):
            for y in range(5):
                idx = x + 5 * y
                state[idx] = (state[idx] ^ d[x]) & MASK_64

        b = [0] * 25
        for x in range(5):
            for y in range(5):
                idx = x + 5 * y
                new_x = y
                new_y = (2 * x + 3 * y) % 5
                b[new_x + 5 * new_y] = _rotl64(state[idx], ROTATION_OFFSETS[x][y])

        for x in range(5):
            for y in range(5):
                idx = x + 5 * y
                state[idx] = (
                    b[idx] ^ ((~b[(x + 1) % 5 + 5 * y] & MASK_64) & b[(x + 2) % 5 + 5 * y])
                ) & MASK_64

        state[0] ^= rc
        state[0] &= MASK_64

def keccak(data: bytes | bytearray | None = None, *, text: str | None = None, hexstr: str | None = None) -> bytes:
    provided = sum(v is not None for v in (data, text, hexstr))
    if provided != 1:
        raise TypeError("keccak() requires exactly one input source")

    if text is not None:
        data_bytes = text.encode("utf-8")
    elif hexstr is not None:
        cleaned = hexstr[2:] if hexstr.startswith("0x") else hexstr
        if len(cleaned) % 2:
            cleaned = "0" + cleaned
        data_bytes = bytes.fromhex(cleaned)
    else:
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("keccak() data must be bytes-like")
        data_bytes = bytes(data)

    rate = 136
    state = [0] * 25
    padded = bytearray(data_bytes)
    padded.append(0x01)
    padded.extend(b"\x00" * ((-len(padded) - 1) % rate))
    padded.append(0x80)

    for offset in range(0, len(padded), rate):
        block = padded[offset : offset + rate]
        for i in range(rate // 8):
            lane = int.from_bytes(block[i * 8 : (i + 1) * 8], "little")
            state[i] = (state[i] ^ lane) & MASK_64
        _keccak_f(state)

    out = bytearray()
    while len(out) < 32:
        for lane in state[: rate // 8]:
            out.extend(lane.to_bytes(8, "little"))
        if len(out) >= 32:
            break
        _keccak_f(state)

    return bytes(out[:32])

def to_hex(value: bytes | bytearray | int) -> str:
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    if isinstance(value, int):
        if value < 0:
            raise ValueError("Cannot convert negative integers to hex")
        return hex(value)
    raise TypeError("Unsupported type for to_hex")

# === CONFIGURATION ===

VAULTS = [
    "0xdfC24b077bC1425Ad1DeA75BCB6F8158E10Df303",
    # Add more vaults here
]

FUNCTION_SIGNATURES = [
    "syncLightDrop(bytes32,uint256)",
    "withdrawRoyalty(address)",
    "claimKinVault(address,uint256)",
    "setSoulSyncVerifier(address)",
    "mintSigilNFT(uint256,bytes32)",
]

# === UTILITIES ===

def get_bytecode(address: str) -> str:
    """Fetch deployed bytecode from Hyperliquid RPC."""
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getCode",
        "params": [address, "latest"],
        "id": 1
    }

    try:
        request = urllib.request.Request(
            "https://rpc.hyperliquid.xyz/evm",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        print(f"⚠️  RPC request failed: {exc}")
        return ""

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        print("⚠️  Received invalid JSON from RPC endpoint")
        return ""

    return parsed.get("result", "") or ""

def get_selector(signature: str) -> str:
    """Convert function signature to 4-byte selector."""
    return to_hex(keccak(text=signature)[:4])

# === MAIN ===

def main():
    print(f"🧬 Checking {len(VAULTS)} vault(s) for SolaraKin signature match...\n")
    selectors = [get_selector(sig) for sig in FUNCTION_SIGNATURES]

    for vault in VAULTS:
        bytecode = get_bytecode(vault).lower()
        print(f"🔍 Scanning vault: {vault}")
        matches = [sig for sig, sel in zip(FUNCTION_SIGNATURES, selectors) if sel in bytecode]

        if matches:
            print(f"✅ MATCH FOUND:")
            for m in matches:
                print(f"  • {m}")
        else:
            print(f"❌ No match.")
        print("—" * 50)

if __name__ == "__main__":
    main()
