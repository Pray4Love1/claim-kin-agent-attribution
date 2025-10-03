"""Helpers for working with the VaultScannerV2WithSig deployment package."""

from __future__ import annotations

import json
from binascii import Error as BinasciiError
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Sequence, Tuple

PACKAGE_FILENAME = "vault_scanner_v2_deployment.json"
PACKAGE_PATH = Path(__file__).resolve().parent / PACKAGE_FILENAME


def load_package() -> Dict[str, Any]:
    """Load the VaultScannerV2WithSig deployment package from disk."""

    with PACKAGE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _strip_0x(value: str) -> str:
    value = value.strip()
    if value.startswith("0x") or value.startswith("0X"):
        return value[2:]
    return value


def _decode_hex(value: str, *, expected_bytes: int, label: str) -> bytes:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be provided as a hex string")
    stripped = _strip_0x(value)
    if len(stripped) != expected_bytes * 2:
        raise ValueError(
            f"{label} must be {expected_bytes} bytes (got {len(stripped) // 2} bytes from '{value}')"
        )
    try:
        return bytes.fromhex(stripped)
    except (ValueError, BinasciiError) as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"{label} must be valid hex: {value}") from exc


def _encode_uint256(value: int, *, label: str) -> bytes:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer (got {value!r})")
    return value.to_bytes(32, "big")


def build_claim_payload(
    user: str, vault_id: str, balance: int, attribution_hash: str
) -> bytes:
    """Return the packed payload used for claim signatures.

    The contract computes ``keccak256(abi.encodePacked(user, vaultId, balance, attributionHash))``.
    This helper recreates the packed data using Python primitives so the digest can be calculated
    and signed off-chain without requiring ``eth_abi`` or similar dependencies.
    """

    address_bytes = _decode_hex(user, expected_bytes=20, label="user address")
    vault_bytes = _decode_hex(vault_id, expected_bytes=32, label="vaultId")
    attribution_bytes = _decode_hex(attribution_hash, expected_bytes=32, label="attributionHash")
    balance_bytes = _encode_uint256(balance, label="balance")
    return address_bytes + vault_bytes + balance_bytes + attribution_bytes


def claim_digest(user: str, vault_id: str, balance: int, attribution_hash: str) -> bytes:
    """Return ``keccak256`` of the packed claim payload."""

    payload = build_claim_payload(user, vault_id, balance, attribution_hash)
    return keccak256(payload)


def ethereum_signed_message_hash(message: bytes) -> bytes:
    """Return the ``toEthSignedMessageHash`` of *message*.

    This mirrors ``ECDSA.toEthSignedMessageHash`` inside the contract so signatures can be
    reproduced or verified in pure Python.
    """

    prefix = f"\x19Ethereum Signed Message:\n{len(message)}".encode("ascii")
    return keccak256(prefix + message)


def claim_message_hash(user: str, vault_id: str, balance: int, attribution_hash: str) -> bytes:
    """Return the final digest that should be signed by the keeper."""

    return ethereum_signed_message_hash(claim_digest(user, vault_id, balance, attribution_hash))


def _rotl(value: int, shift: int) -> int:
    return ((value << shift) & 0xFFFFFFFFFFFFFFFF) | (value >> (64 - shift))


_ROTATION_OFFSETS = (
    (0, 36, 3, 41, 18),
    (1, 44, 10, 45, 2),
    (62, 6, 43, 15, 61),
    (28, 55, 25, 21, 56),
    (27, 20, 39, 8, 14),
)

_ROUND_CONSTANTS = (
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


def _keccak_f(state: List[int]) -> None:
    for round_constant in _ROUND_CONSTANTS:
        # θ step
        c = [0] * 5
        for x in range(5):
            c[x] = (
                state[x]
                ^ state[x + 5]
                ^ state[x + 10]
                ^ state[x + 15]
                ^ state[x + 20]
            )
        d = [0] * 5
        for x in range(5):
            d[x] = c[(x - 1) % 5] ^ _rotl(c[(x + 1) % 5], 1)
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] ^= d[x]

        # ρ and π steps combined
        new_state = [0] * 25
        for x in range(5):
            for y in range(5):
                index = x + 5 * y
                new_x = y
                new_y = (2 * x + 3 * y) % 5
                shift = _ROTATION_OFFSETS[x][y]
                new_state[new_x + 5 * new_y] = _rotl(state[index], shift)
        state[:] = new_state

        # χ step
        for y in range(5):
            row = state[5 * y : 5 * y + 5]
            for x in range(5):
                state[5 * y + x] = row[x] ^ ((~row[(x + 1) % 5]) & row[(x + 2) % 5])

        # ι step
        state[0] ^= round_constant


def keccak256(data: bytes) -> bytes:
    """Return the Keccak-256 hash of *data*."""

    rate_bytes = 136
    state = [0] * 25

    # Absorb full-rate blocks directly from the input.
    data_len = len(data)
    offset = 0
    while offset + rate_bytes <= data_len:
        block = data[offset : offset + rate_bytes]
        offset += rate_bytes
        for i in range(0, rate_bytes, 8):
            chunk = block[i : i + 8]
            state[i // 8] ^= int.from_bytes(chunk, "little")
        _keccak_f(state)

    # Absorb the final padded block (always processed, even for empty input).
    remainder = data[offset:]
    block = bytearray(rate_bytes)
    block[: len(remainder)] = remainder
    block[len(remainder)] ^= 0x01
    block[-1] ^= 0x80
    for i in range(0, rate_bytes, 8):
        chunk = block[i : i + 8]
        state[i // 8] ^= int.from_bytes(chunk, "little")
    _keccak_f(state)

    # Squeeze phase
    output = bytearray()
    while len(output) < 32:
        for lane in state[: rate_bytes // 8]:
            output.extend(lane.to_bytes(8, "little"))
        if len(output) >= 32:
            break
        _keccak_f(state)
    return bytes(output[:32])


def iter_function_entries(abi: Sequence[Mapping[str, Any]]) -> Iterator[Mapping[str, Any]]:
    """Yield each function entry from an ABI list."""

    for entry in abi:
        if isinstance(entry, Mapping) and entry.get("type") == "function":
            yield entry


def canonical_signature(entry: Mapping[str, Any]) -> str:
    """Return the canonical signature string for a function ABI entry."""

    name = str(entry.get("name", "<unnamed>"))
    inputs = entry.get("inputs", [])
    if not isinstance(inputs, Sequence):
        inputs = []
    types: List[str] = []
    for item in inputs:
        if isinstance(item, Mapping):
            types.append(str(item.get("type", "")))
        else:
            types.append("")
    return f"{name}({','.join(types)})"


def describe_function(entry: Mapping[str, Any]) -> str:
    """Format a function entry as a human-readable description."""

    name = str(entry.get("name", "<unnamed>"))
    inputs = entry.get("inputs", [])
    if not isinstance(inputs, Sequence):
        inputs = []
    formatted_inputs: List[str] = []
    for item in inputs:
        if isinstance(item, Mapping):
            internal_type = str(item.get("internalType", item.get("type", "<unknown>")))
            arg_name = str(item.get("name", ""))
            formatted_inputs.append(f"{internal_type} {arg_name}".strip())
        else:
            formatted_inputs.append("<unknown>")
    state = str(entry.get("stateMutability", ""))
    return f"{name}({', '.join(formatted_inputs)}) [{state}]"


def describe_functions(abi: Sequence[Mapping[str, Any]]) -> List[str]:
    """Return descriptions for all functions in an ABI."""

    return [describe_function(entry) for entry in iter_function_entries(abi)]


def function_selectors(abi: Sequence[Mapping[str, Any]]) -> Dict[str, str]:
    """Return a mapping of canonical signatures to 4-byte selectors."""

    selectors: Dict[str, str] = {}
    for entry in iter_function_entries(abi):
        signature = canonical_signature(entry)
        selector_bytes = keccak256(signature.encode("utf-8"))[:4]
        selectors[signature] = "0x" + selector_bytes.hex()
    return selectors


def selectors_by_name(abi: Sequence[Mapping[str, Any]]) -> Dict[str, str]:
    """Return a mapping of function name to selector for the ABI."""

    mapping: Dict[str, str] = {}
    for entry in iter_function_entries(abi):
        name = str(entry.get("name", ""))
        signature = canonical_signature(entry)
        mapping[name] = function_selectors([entry])[signature]
    return mapping


def selectors_with_signatures(abi: Sequence[Mapping[str, Any]]) -> Dict[str, Tuple[str, str]]:
    """Return mapping of function name to (signature, selector)."""

    result: Dict[str, Tuple[str, str]] = {}
    selectors = function_selectors(abi)
    for entry in iter_function_entries(abi):
        name = str(entry.get("name", ""))
        signature = canonical_signature(entry)
        selector = selectors[signature]
        result[name] = (signature, selector)
    return result
