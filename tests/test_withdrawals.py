from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from claim_kin_agent_attribution.withdrawals import load_api_wallet, perform_withdrawal


class DummyExchange:
    def __init__(self, wallet, base_url, account_address=None):  # noqa: D401 - test double
        self.wallet = wallet
        self.base_url = base_url
        self.account_address = account_address
        self.calls: list[tuple[float, str]] = []

    def withdraw_from_bridge(self, amount: float, destination: str):  # noqa: D401 - test double
        self.calls.append((amount, destination))
        return {"amount": amount, "destination": destination}


def test_load_api_wallet_prefers_configured_account(monkeypatch):
    captured_secret = "0x1"
    fake_account = SimpleNamespace(address="0xabc123")

    def fake_from_key(value):
        assert value == captured_secret
        return fake_account

    monkeypatch.setenv("HL_API_KEY", captured_secret)
    monkeypatch.setenv("HL_ACCOUNT_ADDRESS", "0xdeadbeef")
    monkeypatch.setattr("claim_kin_agent_attribution.withdrawals.Account.from_key", fake_from_key)

    account, address = load_api_wallet({
        "HL_API_KEY": captured_secret,
        "HL_ACCOUNT_ADDRESS": "0xdeadbeef",
    })

    assert account is fake_account
    assert address == "0xdeadbeef"


def test_load_api_wallet_raises_when_missing_key():
    with pytest.raises(RuntimeError):
        load_api_wallet({})


def test_perform_withdrawal_invokes_exchange(monkeypatch):
    wallet = SimpleNamespace()
    exchange = DummyExchange(wallet, "https://api.example", account_address="0xabc")

    def factory(wallet_arg, base_url, account_address=None):
        assert wallet_arg is wallet
        assert base_url == "https://api.example"
        assert account_address == "0xabc"
        return exchange

    response = perform_withdrawal(
        Decimal("123.45"),
        "0xfeed",
        wallet,
        base_url="https://api.example",
        account_address="0xabc",
        exchange_cls=factory,  # type: ignore[arg-type]
    )

    assert response == {"amount": 123.45, "destination": "0xfeed"}
    assert exchange.calls == [(123.45, "0xfeed")]


def test_perform_withdrawal_rejects_non_positive_amount(wallet_address="0xabc"):
    wallet = SimpleNamespace(address=wallet_address)
    with pytest.raises(ValueError):
        perform_withdrawal(Decimal("0"), "0xfeed", wallet, account_address=wallet_address)


def test_cli_allows_account_override(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import scripts.codex_trigger_hyperliquid_withdrawal as cli

    wallet = SimpleNamespace()
    monkeypatch.setattr(cli, "load_api_wallet", lambda: (wallet, "0xdefault"))

    captured: dict[str, object] = {}

    def fake_perform(amount, destination, wallet_obj, *, base_url=None, account_address, exchange_cls=None):
        captured.update(
            amount=amount,
            destination=destination,
            wallet=wallet_obj,
            base_url=base_url,
            account=account_address,
        )
        return {"status": "ok"}

    monkeypatch.setattr(cli, "perform_withdrawal", fake_perform)

    assert (
        cli.main(
            [
                "--amount",
                "10",
                "--account",
                "0xoverride",
                "--destination",
                "0xfeed",
                "--json",
            ]
        )
        == 0
    )
    assert captured["account"] == "0xoverride"
    assert captured["wallet"] is wallet
    assert captured["destination"] == "0xfeed"
    assert captured["amount"] == Decimal("10")
    assert json.loads(capsys.readouterr().out)["status"] == "ok"


def test_cli_defaults_to_configured_account(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.codex_trigger_hyperliquid_withdrawal as cli

    wallet = SimpleNamespace()
    monkeypatch.setattr(cli, "load_api_wallet", lambda: (wallet, "0xconfigured"))

    captured: dict[str, object] = {}

    def fake_perform(amount, destination, wallet_obj, *, base_url=None, account_address, exchange_cls=None):
        captured.update(account=account_address)
        return {"status": "ok"}

    monkeypatch.setattr(cli, "perform_withdrawal", fake_perform)

    assert cli.main(["--amount", "5", "--destination", "0xfeed", "--json"]) == 0
    assert captured["account"] == "0xconfigured"
