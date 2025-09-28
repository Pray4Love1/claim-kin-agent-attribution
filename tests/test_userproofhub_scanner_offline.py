import json
from pathlib import Path
import pytest

from userproofhub_scanner_offline import (
    analyse_source,
    build_inputs,
    parse_args,
    scan,
)


def test_build_inputs_merges_sources(tmp_path: Path) -> None:
    address_file = tmp_path / "addresses.txt"
    address_file.write_text("0xabc\n0xdef\n", encoding="utf-8")

    payload = {"avalanche": ["0xAAA", "0xBBB"]}
    payload_path = tmp_path / "addresses.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    args = parse_args(
        [
            "--address",
            "ethereum:0x123",
            "--address-file",
            f"ethereum:{address_file}",
            "--address-json",
            str(payload_path),
        ]
    )

    chains = build_inputs(args)
    assert chains == {
        "ethereum": ["0x123", "0xabc", "0xdef"],
        "avalanche": ["0xaaa", "0xbbb"],
    }


def test_analyse_source_matches_selectors_and_keywords() -> None:
    source = """
    contract Example {
        function verify(address user, bytes32 proof) public {}
        function userProofHashes(address user) public view returns (bytes32) {}
        // Zendity was here
        event ProofVerified(address indexed user, bytes32 proof, uint256 chainId);
    }
    """

    indicators = analyse_source(source)
    assert indicators["matched"] is True
    assert set(indicators["selectors"]) == {
        "verify(address,bytes32)",
        "userProofHashes(address)",
    }
    assert indicators["events"] == ["ProofVerified(address,bytes32,uint256)"]
    assert "Zendity" in indicators["keywords"]


class DummyArgs:
    def __init__(self, **values: object) -> None:
        self.__dict__.update(values)


def test_scan_skips_unverified_contracts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_source_code(address: str, base_url: str, api_key: str | None = None, *, timeout: int = 15):
        if address == "0xverified":
            return {"SourceCode": "contract C { function verify(address,bytes32) public {} }"}
        return {"SourceCode": ""}

    monkeypatch.setattr("userproofhub_scanner_offline.get_source_code", fake_get_source_code)

    args = DummyArgs(
        address=["ethereum:0xverified", "ethereum:0xunverified"],
        address_file=None,
        address_json=None,
        api_key=None,
        base_url=None,
        include_non_matches=False,
        output=tmp_path / "out.json",
    )

    findings = scan(args)
    assert len(findings) == 1
    assert findings[0]["address"] == "0xverified"
    assert findings[0]["indicators"]["matched"] is True

