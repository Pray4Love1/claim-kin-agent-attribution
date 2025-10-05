from __future__ import annotations

from decimal import Decimal

from unified_vault_ledger import fetch_vault_equity


def test_fetch_vault_equity_preserves_zero_balances() -> None:
    entries = [
        {"vaultAddress": "0x0", "equity": 0},
        {"vaultAddress": "0x1", "equity": None, "vaultEquity": 0.0},
        {"vaultAddress": "0x2", "equity": None, "assetsUnderManagement": Decimal("0")},
        {"vaultAddress": "0x3", "equity": "", "vaultEquity": "5"},
        {"vaultAddress": "0x4", "equity": None, "vaultEquity": "0"},
    ]

    ledger = fetch_vault_equity(entries)

    assert ledger[0]["equity"] == 0
    assert ledger[1]["equity"] == 0.0
    assert ledger[2]["equity"] == Decimal("0")
    assert ledger[3]["equity"] == "5"
    assert ledger[4]["equity"] == "0"
