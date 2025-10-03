"""Tests for withdrawable balance extraction helpers."""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

from claim_kin_agent_attribution.balances import extract_withdrawable_balance


class _FakeInfo:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def user_state(self, address: str, **kwargs: object) -> dict[str, object]:  # noqa: D401 - simple stub
        return self._payload


class _RecordingInfo(_FakeInfo):
    def __init__(self, payload: dict[str, object]) -> None:
        super().__init__(payload)
        self.calls: list[dict[str, object]] = []

    def user_state(self, address: str, **kwargs: object) -> dict[str, object]:
        self.calls.append({"address": address, "kwargs": kwargs})
        return super().user_state(address, **kwargs)


@pytest.fixture()
def example_user_state() -> dict[str, object]:
    return {
        "clearinghouseState": {
            "withdrawable": "1010.57173",
        }
    }


def test_extract_withdrawable_balance_returns_decimal(example_user_state: dict[str, object]) -> None:
    balance = extract_withdrawable_balance(example_user_state)
    assert isinstance(balance, Decimal)
    assert balance == Decimal("1010.57173")


def test_extract_withdrawable_balance_missing_field_raises() -> None:
    with pytest.raises(ValueError):
        extract_withdrawable_balance({})


def test_cli_outputs_human_readable(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import scripts.find_balance as cli

    payload = {"clearinghouseState": {"withdrawable": "42.5"}}

    monkeypatch.setattr(cli, "Info", lambda skip_ws=True: _FakeInfo(payload))

    assert cli.main(["0xabc"]) == 0
    out = capsys.readouterr().out
    assert "Withdrawable balance" in out
    assert "$42.50" in out


def test_cli_outputs_json(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import scripts.find_balance as cli

    payload = {"clearinghouseState": {"withdrawable": "123.4567"}}
    monkeypatch.setattr(cli, "Info", lambda skip_ws=True: _FakeInfo(payload))

    assert cli.main(["0xabc", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["withdrawable_usd"] == "123.4567"
    assert data["address"] == "0xabc"


def test_cli_omits_blank_dex(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import scripts.find_balance as cli

    payload = {"clearinghouseState": {"withdrawable": "8.5"}}
    recording_info = _RecordingInfo(payload)
    monkeypatch.setattr(cli, "Info", lambda skip_ws=True: recording_info)

    assert cli.main(["0xabc", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["dex"] is None
    assert recording_info.calls == [
        {
            "address": "0xabc",
            "kwargs": {},
        }
    ]