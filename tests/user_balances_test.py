import pytest

from hyperliquid.info import Info

TEST_META = {"universe": []}
TEST_SPOT_META = {
    "universe": [
        {"tokens": [0, 1], "name": "PURR/USDC", "index": 0, "isCanonical": True}
    ],
    "tokens": [
        {
            "name": "PURR",
            "szDecimals": 6,
            "weiDecimals": 6,
            "index": 0,
            "tokenId": "PURR",
            "isCanonical": True,
            "evmContract": None,
            "fullName": None,
        },
        {
            "name": "USDC",
            "szDecimals": 6,
            "weiDecimals": 6,
            "index": 1,
            "tokenId": "USDC",
            "isCanonical": True,
            "evmContract": None,
            "fullName": None,
        },
    ],
}


@pytest.fixture(name="info_instance")
def _info_instance():
    return Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)


def test_user_balances_filters_zero_entries(monkeypatch, info_instance):
    def fake_user_state(self, address, dex=""):
        return {
            "assetPositions": [
                {
                    "position": {
                        "coin": "BTC",
                        "szi": "0.1",
                        "positionValue": "1000.0",
                        "unrealizedPnl": "10.0",
                        "marginUsed": "50.0",
                    }
                },
                {
                    "position": {
                        "coin": "ETH",
                        "szi": "0",
                        "positionValue": "0",
                        "unrealizedPnl": "0",
                        "marginUsed": "0",
                    }
                },
            ],
            "marginSummary": {"accountValue": "1500.0"},
            "withdrawable": "100.0",
        }

    def fake_spot_state(self, address):
        return {
            "balances": [
                {"token": 0, "total": "0", "available": "0", "usdValue": "0"},
                {"token": 1, "total": "5.123456", "available": "5.023456", "usdValue": "50.25"},
            ]
        }

    monkeypatch.setattr(Info, "user_state", fake_user_state)
    monkeypatch.setattr(Info, "spot_user_state", fake_spot_state)

    balances = info_instance.user_balances("0xabc")

    assert balances["perp"]["accountValue"] == pytest.approx(1500.0)
    assert balances["perp"]["withdrawable"] == pytest.approx(100.0)

    perp_positions = balances["perp"]["positions"]
    assert len(perp_positions) == 1
    assert perp_positions[0]["coin"] == "BTC"
    assert perp_positions[0]["size"] == pytest.approx(0.1)
    assert perp_positions[0]["positionValue"] == pytest.approx(1000.0)
    assert perp_positions[0]["unrealizedPnl"] == pytest.approx(10.0)

    spot_balances = balances["spot"]["balances"]
    assert len(spot_balances) == 1
    assert spot_balances[0]["token"] == 1
    assert spot_balances[0]["tokenName"] == "USDC"
    assert spot_balances[0]["total"] == pytest.approx(5.123456)
    assert spot_balances[0]["available"] == pytest.approx(5.023456)
    assert spot_balances[0]["usdValue"] == pytest.approx(50.25)

    all_balances = info_instance.user_balances("0xabc", include_zero=True)
    assert len(all_balances["perp"]["positions"]) == 2
    assert len(all_balances["spot"]["balances"]) == 2
