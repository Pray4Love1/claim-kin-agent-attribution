import pytest

eth_account = pytest.importorskip("eth_account")

from hyperliquid.exchange import Exchange
from hyperliquid.utils.constants import MAINNET_API_URL
from hyperliquid.utils.signing import order_request_to_order_wire, order_wires_to_order_action
from hyperliquid.utils.types import Meta, SpotMeta


TEST_META: Meta = {"universe": [{"name": "ETH", "szDecimals": 4}]}
TEST_SPOT_META: SpotMeta = {"universe": [], "tokens": []}


def _create_exchange() -> Exchange:
    wallet = eth_account.Account.from_key(
        "0x0123456789012345678901234567890123456789012345678901234567890123"
    )
    return Exchange(
        wallet,
        base_url=MAINNET_API_URL,
        meta=TEST_META,
        spot_meta=TEST_SPOT_META,
        vault_address="0x1719884eb866cb12b2287399b15f7db5e7d775ea",
    )


def test_bulk_orders_tx_records_unsigned_payload(monkeypatch):
    exchange = _create_exchange()

    fixed_timestamp = 1_687_000_000_000
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
    asset = exchange.info.name_to_asset(order_request["coin"])
    expected_action = order_wires_to_order_action([
        order_request_to_order_wire(order_request, asset)
    ])

    pending = exchange.pending_unsigned_actions()
    assert len(pending) == 1
    record = pending[0]
    assert record["signer"] == exchange.wallet.address.lower()
    assert record["typedData"] == payload
    assert record["nonce"] == fixed_timestamp
    assert record["vaultAddress"] == exchange.vault_address
    assert record["expiresAfter"] == exchange.expires_after
    assert record["action"] == expected_action


def test_clear_unsigned_actions(monkeypatch):
    exchange = _create_exchange()
    monkeypatch.setattr("hyperliquid.exchange.get_timestamp_ms", lambda: 1234)

    order_request = {
        "coin": "ETH",
        "is_buy": True,
        "sz": 1.0,
        "limit_px": 1000.0,
        "reduce_only": False,
        "order_type": {"limit": {"tif": "Gtc"}},
    }

    exchange.bulk_orders_tx([order_request])
    assert exchange.pending_unsigned_actions(exchange.wallet.address)

    exchange.clear_unsigned_actions(exchange.wallet.address)
    assert exchange.pending_unsigned_actions(exchange.wallet.address) == []
    assert exchange.pending_unsigned_actions() == []

