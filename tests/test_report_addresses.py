import json
from pathlib import Path

import pytest

from codex_attribution.report_addresses import extract_addresses, main


@pytest.fixture()
def report_dir(tmp_path: Path) -> Path:
    base = tmp_path / "ava_userproofhub_claim"
    base.mkdir()
    (base / "selector_matches.csv").write_text(
        "contract_address,chain\n"
        "0xAAAABBBBCCCCDDDDEEEEFFFF0000111122223333,ethereum\n"
        "0xaaaabbbbccccddddeeeeffff0000111122223333,ethereum\n"
        "0xDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF,avalanche\n",
        encoding="utf-8",
    )
    (base / "proof_overlap_report.json").write_text(
        json.dumps({"proof_bundle": ["selector_matches.csv"]}),
        encoding="utf-8",
    )
    return base


def test_extract_addresses_deduplicates_and_preserves_order(report_dir: Path) -> None:
    report_path = report_dir / "proof_overlap_report.json"
    addresses = extract_addresses(report_path)
    assert addresses == [
        "0xAAAABBBBCCCCDDDDEEEEFFFF0000111122223333",
        "0xDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF",
    ]


def test_main_prints_addresses(capsys: pytest.CaptureFixture[str], report_dir: Path) -> None:
    report_path = report_dir / "proof_overlap_report.json"
    main([str(report_path)])
    captured = capsys.readouterr()
    lines = [line for line in captured.out.strip().splitlines() if line]
    assert lines == [
        "0xAAAABBBBCCCCDDDDEEEEFFFF0000111122223333",
        "0xDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF",
    ]
