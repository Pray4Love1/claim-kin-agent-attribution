from __future__ import annotations

import pytest

eth_account = pytest.importorskip("eth_account")

from hyperliquid.exchange import Exchange
from hyperliquid.utils.constants import MAINNET_API_URL
from hyperliquid.utils.signing import (
    get_l1_action_data,
    order_request_to_order_wire,
    order_wires_to_order_action,
)
from hyperliquid.utils.types import Meta, SpotMeta

TEST_META: Meta = {"universe": [{"name": "ETH", "szDecimals": 4}]}
TEST_SPOT_META: SpotMeta = {"universe": [], "tokens": {}}


def _create_exchange() -> Exchange:
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    return Exchange(
        wallet,
        base_url=MAINNET_API_URL,
        meta=TEST_META,
        spot_meta=TEST_SPOT_META,
        vault_address="0x1719884eb866cb12b2287399b15f7db5e7d775ea",
    )


def test_bulk_orders_tx_returns_unsigned_payload(monkeypatch):
    exchange = _create_exchange()

    fixed_timestamp = 1_700_000_000_000
    monkeypatch.setattr("hyperliquid.exchange.get_timestamp_ms", lambda: fixed_timestamp)

    order_request = {
        "coin": "ETH",
        "is_buy": True,
        "sz": 1.0,
        "limit_px": 1000.0,
        "reduce_only": False,
        "order_type": {"limit": {"tif": "Gtc"}},
    }

    payload = exchange.bulk_orders_tx([order_request])

    assert payload["nonce"] == fixed_timestamp
    assert payload["vault_address"] == exchange.vault_address
    assert payload["expires_after"] == exchange.expires_after

    asset = exchange.info.name_to_asset(order_request["coin"])
    expected_action = order_wires_to_order_action([order_request_to_order_wire(order_request, asset)])
    assert payload["action"] == expected_action

    expected_typed_data = get_l1_action_data(
        expected_action,
        exchange.vault_address,
        fixed_timestamp,
        exchange.expires_after,
        True,
    )
    assert payload["typed_data"] == expected_typed_data


def test_submit_signed_action_posts_payload(monkeypatch):
    exchange = _create_exchange()

    captured = {}

    def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {"status": "ok"}

    monkeypatch.setattr(exchange, "post", fake_post)

    action = {"type": "dummy"}
    signature = {"r": "0x1", "s": "0x2", "v": 27}
    nonce = 123

    response = exchange.submit_signed_action(action, signature, nonce)

    assert response == {"status": "ok"}
    assert captured["path"] == "/exchange"
    assert captured["payload"]["action"] == action
    assert captured["payload"]["signature"] == signature
    assert captured["payload"]["nonce"] == nonce
