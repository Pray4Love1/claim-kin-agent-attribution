"""Tests for extracting builder referral codes from metadata payloads."""
from __future__ import annotations

import json
from typing import Any, Iterable, List

import pytest

from claim_kin_agent_attribution.builder_codes import (
    fetch_builder_codes,
    filter_builder_codes,
    parse_builder_codes,
)


class _FakeInfo:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def perp_dexs(self) -> Any:
        return self._payload


@pytest.fixture()
def sample_payload() -> List[dict[str, Any]]:
    return [
        {"name": "", "description": "core"},
        {
            "name": "solarak1n",
            "builder": {
                "address": "0x1111111111111111111111111111111111111111",
                "code": "SOLARA",
                "shareBps": "25",
            },
        },
        {
            "name": "keeper_f303",
            "builderAddress": "0x2222222222222222222222222222222222222222",
            "builderCode": "F303",
            "feeShareBps": 40,
        },
        {
            "name": "atlas_core",
            "builder": {
                "addr": "0x3333333333333333333333333333333333333333",
                "referralCode": "ATLAS",
                "bps": "12",
            },
        },
        {"name": "orphan", "description": "missing builder data"},
    ]


def test_parse_builder_codes_handles_varied_payloads(sample_payload: Iterable[dict[str, Any]]) -> None:
    codes = parse_builder_codes(sample_payload)
    assert [code.dex for code in codes] == ["solarak1n", "keeper_f303", "atlas_core"]
    assert codes[0].builder_address == "0x1111111111111111111111111111111111111111"
    assert codes[0].code == "SOLARA"
    assert codes[0].share_bps == 25
    assert codes[1].share_bps == 40
    assert codes[2].share_bps == 12


def test_fetch_builder_codes_uses_info(sample_payload: Iterable[dict[str, Any]]) -> None:
    info = _FakeInfo(sample_payload)
    codes = fetch_builder_codes(info)  # type: ignore[arg-type]
    assert len(codes) == 3


def test_filter_builder_codes_restricts_to_known_addresses(sample_payload: Iterable[dict[str, Any]]) -> None:
    codes = parse_builder_codes(sample_payload)
    filtered = filter_builder_codes(codes, ["0x3333333333333333333333333333333333333333"])
    assert [code.dex for code in filtered] == ["atlas_core"]


def test_builder_code_serialisation_contains_metadata(sample_payload: Iterable[dict[str, Any]]) -> None:
    codes = parse_builder_codes(sample_payload)
    payload = codes[0].as_dict()
    assert payload["dex"] == "solarak1n"
    assert payload["builder_address"].startswith("0x1111")
    metadata = payload["metadata"]
    assert json.loads(json.dumps(metadata))  # ensure serialisable


def test_cli_outputs_expected_json(monkeypatch: pytest.MonkeyPatch, sample_payload: List[dict[str, Any]], capsys) -> None:
    import scripts.find_builder_codes as cli

    class _Info:
        def __init__(self, api_url: str, skip_ws: bool) -> None:  # noqa: D401 - simple stub
            self._payload = sample_payload

        def perp_dexs(self) -> Any:
            return self._payload

    monkeypatch.setattr(cli, "Info", _Info)

    assert cli.main(["--json"]) == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["count"] == 3
    assert {entry["dex"] for entry in payload["builder_codes"]} == {"solarak1n", "keeper_f303", "atlas_core"}
