"""Regression tests for the Codex Vault Inspector helpers."""
from __future__ import annotations

import pytest

import scripts.query_all_vaults as cli


OWNER = "0xb2b297eF9449aa0905bC318B3bd258c4804BAd98"
VAULT = "0x0000000000000000000000000000000000001000"


def test_zip_components_creates_entries() -> None:
    entries = cli._zip_components(
        OWNER,
        ([VAULT], ["0x64"], [b"\x12"], ["0x5"]),
    )

    assert len(entries) == 1
    entry = entries[0]
    assert entry.owner == OWNER
    assert entry.vault == cli._as_checksum(VAULT)
    assert entry.balance == 0x64
    assert entry.attribution_hash == "0x12"
    assert entry.updated_at == 5


def test_normalise_owner_payload_handles_struct_list() -> None:
    payload = [
        (VAULT, 500, "0xab", 1234567890),
    ]
    entries = cli._normalise_owner_payload(OWNER, payload)
    assert len(entries) == 1
    assert entries[0].balance == 500
    assert entries[0].attribution_hash == "0xab"
    assert entries[0].updated_at == 1234567890


def test_normalise_owner_payload_handles_dict_components() -> None:
    payload = {
        "vaults": [VAULT],
        "balances": [1],
        "attributionHashes": [b""],
        "timestamps": ["0x7b"],
    }
    entries = cli._normalise_owner_payload(OWNER, payload)
    assert len(entries) == 1
    assert entries[0].updated_at == 123


def test_collect_entries_supports_dict_response(monkeypatch: pytest.MonkeyPatch) -> None:
    response = {
        OWNER: {
            "vaults": [VAULT],
            "balances": [2],
            "attributionHashes": ["0x99"],
            "timestamps": [3],
        }
    }

    monkeypatch.setattr(cli, "_call_scanner", lambda contract, method, owners: response)

    entries = cli._collect_entries(object(), "query", [OWNER])
    assert len(entries) == 1
    assert entries[0].balance == 2
    assert entries[0].attribution_hash == "0x99"
    assert entries[0].updated_at == 3


def test_resolve_method_prefers_explicit() -> None:
    class _FnContainer:
        query = object()

    class _Contract:
        functions = _FnContainer()

    assert cli._resolve_method(_Contract(), "query") == "query"


def test_resolve_method_autodetects_first_candidate() -> None:
    class _FnContainer:
        getVaultsForOwners = object()

    class _Contract:
        functions = _FnContainer()

    assert cli._resolve_method(_Contract(), None) == "getVaultsForOwners"


def test_normalise_owner_payload_rejects_unknown_shape() -> None:
    with pytest.raises(cli.VaultScannerError):
        cli._normalise_owner_payload(OWNER, "unexpected")
