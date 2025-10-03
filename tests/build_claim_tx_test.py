import argparse
import json
from pathlib import Path

import pytest

from scripts.build_claim_tx import build_claim_transaction_from_args


def _namespace(**kwargs):
    return argparse.Namespace(**kwargs)


def test_build_claim_transaction_from_args_infers_user(tmp_path: Path) -> None:
    claim_file = tmp_path / "claim.json"
    claim_file.write_text(json.dumps({"linked_wallet": "0x1111111111111111111111111111111111111111"}), encoding="utf-8")

    args = _namespace(
        vault_address="0x2222222222222222222222222222222222222222",
        vault_id="0x" + "33" * 32,
        balance=123,
        attribution_hash="0x" + "44" * 32,
        signature="0x" + "55" * 65,
        user=None,
        claim_file=claim_file,
        chain_id=None,
        gas=None,
        nonce=None,
        sender=None,
    )

    txn = build_claim_transaction_from_args(args)
    assert txn["from"] == "0x1111111111111111111111111111111111111111"
    assert txn["to"] == "0x2222222222222222222222222222222222222222"
    assert txn["value"] == "0x0"
    assert txn["data"].startswith("0x3bb71497")


def test_build_claim_transaction_from_args_requires_user_when_missing(tmp_path: Path) -> None:
    args = _namespace(
        vault_address="0x2222222222222222222222222222222222222222",
        vault_id="0x" + "33" * 32,
        balance=123,
        attribution_hash="0x" + "44" * 32,
        signature="0x" + "55" * 65,
        user=None,
        claim_file=tmp_path / "missing.json",
        chain_id=None,
        gas=None,
        nonce=None,
        sender=None,
    )

    with pytest.raises(ValueError):
        build_claim_transaction_from_args(args)