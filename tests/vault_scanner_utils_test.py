from __future__ import annotations

from typing import Iterable

import pytest

from claims.vault_scanner_utils import (
    _keccak_f,
    build_claim_payload,
    claim_digest,
    claim_message_hash,
    ethereum_signed_message_hash,
    keccak256,
)


@pytest.mark.parametrize(
    "user,vault_id,balance,attribution,expected_prefix",
    [
        (
            "0x000000000000000000000000000000000000dEaD",
            "0x" + "11" * 32,
            123456789,
            "0x" + "22" * 32,
            "000000000000000000000000000000000000dead",
        )
    ],
)
def test_build_claim_payload(user: str, vault_id: str, balance: int, attribution: str, expected_prefix: str) -> None:
    payload = build_claim_payload(user, vault_id, balance, attribution)
    assert len(payload) == 20 + 32 + 32 + 32
    assert payload[:20].hex() == expected_prefix
    assert payload[20:52].hex() == ("11" * 32)
    assert payload[52:84].hex() == balance.to_bytes(32, "big").hex()
    assert payload[84:].hex() == ("22" * 32)


def test_claim_digest_matches_manual_keccak() -> None:
    user = "0x1111111111111111111111111111111111111111"
    vault_id = "0x" + "aa" * 32
    attribution = "0x" + "bb" * 32
    balance = 42

    digest = claim_digest(user, vault_id, balance, attribution)
    # Expected value calculated once the helper was verified against the Solidity implementation.
    assert digest.hex() == "9a424ef49188881d7d1eb0aed233cba56b369449f40e6ee25b90f36b1b12a1ca"


def test_claim_message_hash_matches_prefixed_digest() -> None:
    user = "0x2222222222222222222222222222222222222222"
    vault_id = "0x" + "33" * 32
    attribution = "0x" + "44" * 32
    balance = 500

    digest = claim_digest(user, vault_id, balance, attribution)
    prefixed = ethereum_signed_message_hash(digest)
    helper = claim_message_hash(user, vault_id, balance, attribution)

    assert prefixed == helper
    assert prefixed.hex() == "929db561f95f7034830afea907146c202ea4c6d7728fc40d8f048e99498239ad"


def _keccak256_reference(data: bytes) -> bytes:
    rate_bytes = 136
    state = [0] * 25

    offset = 0
    data_len = len(data)
    while offset + rate_bytes <= data_len:
        block = data[offset : offset + rate_bytes]
        offset += rate_bytes
        for i in range(0, rate_bytes, 8):
            chunk = block[i : i + 8]
            state[i // 8] ^= int.from_bytes(chunk, "little")
        _keccak_f(state)

    remainder = data[offset:]
    block = bytearray(rate_bytes)
    block[: len(remainder)] = remainder
    block[len(remainder)] ^= 0x01
    block[-1] ^= 0x80
    for i in range(0, rate_bytes, 8):
        chunk = block[i : i + 8]
        state[i // 8] ^= int.from_bytes(chunk, "little")
    _keccak_f(state)

    output = bytearray()
    while len(output) < 32:
        for lane in state[: rate_bytes // 8]:
            output.extend(lane.to_bytes(8, "little"))
        if len(output) >= 32:
            break
        _keccak_f(state)
    return bytes(output[:32])


def _pattern(length: int) -> bytes:
    source: Iterable[int] = ((index % 256) for index in range(length))
    return bytes(source)


@pytest.mark.parametrize("length", [0, 1, 31, 32, 135, 136, 137, 200])
def test_keccak256_padding_matches_reference(length: int) -> None:
    data = _pattern(length)
    assert keccak256(data) == _keccak256_reference(data)
