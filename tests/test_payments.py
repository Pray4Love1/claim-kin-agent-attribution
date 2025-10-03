from __future__ import annotations

from decimal import Decimal

import pytest

from claim_kin_agent_attribution.payments import (
    PaymentSettlement,
    extract_payment_settlements,
    total_settlement_amount,
)


def _make_update(time_ms: int, hash_: str, delta: dict[str, str]) -> dict[str, object]:
    return {"time": time_ms, "hash": hash_, "delta": delta}


def test_extract_payment_settlements_handles_deposits_and_transfers():
    updates = [
        _make_update(1, "0xdeposit", {"type": "deposit", "usdc": "2703997.4500000002"}),
        _make_update(2, "0xtransfer", {"type": "accountClassTransfer", "usdc": "-125.5", "toPerp": True}),
        _make_update(
            3,
            "0xspot",
            {
                "type": "spotTransfer",
                "token": "USDC",
                "amount": "10.5",
                "usdcValue": "10.5",
                "destination": "0xabc",
                "fee": "1.0",
                "nativeTokenFee": "0.0",
            },
        ),
        _make_update(4, "0xignored", {"type": "note", "value": "no usd"}),
    ]

    settlements = extract_payment_settlements(updates)
    assert [s.tx_hash for s in settlements] == ["0xdeposit", "0xtransfer", "0xspot"]

    deposit, transfer, spot = settlements
    assert deposit.amount_usd == Decimal("2703997.4500000002")
    assert deposit.direction == "credit"

    assert transfer.amount_usd == Decimal("-125.5")
    assert transfer.direction == "debit"

    assert spot.amount_usd == Decimal("-11.5")
    assert spot.direction == "debit"


def test_total_settlement_amount_sums_signed_amounts():
    settlements = [
        PaymentSettlement(0, "hash1", "deposit", Decimal("100"), "credit", {}),
        PaymentSettlement(0, "hash2", "withdrawal", Decimal("-40.25"), "debit", {}),
    ]
    assert total_settlement_amount(settlements) == Decimal("59.75")


@pytest.mark.parametrize("payload", [[], [{}], [{"delta": {"type": "deposit", "usdc": "0"}}]])
def test_extract_payment_settlements_gracefully_skips_invalid_entries(payload):
    assert extract_payment_settlements(payload) == []
