"""Offline fixtures for hyperliquid.info.Info integration tests."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


_META_UNIVERSE: List[Dict[str, Any]] = [
    {"name": "BTC", "szDecimals": 5, "maxLeverage": 50},
    {"name": "ETH", "szDecimals": 4, "maxLeverage": 50},
    {"name": "ATOM", "szDecimals": 2, "maxLeverage": 50},
    {"name": "MATIC", "szDecimals": 1, "maxLeverage": 50},
    {"name": "DYDX", "szDecimals": 1, "maxLeverage": 50},
    {"name": "SOL", "szDecimals": 2, "maxLeverage": 50},
    {"name": "AVAX", "szDecimals": 2, "maxLeverage": 50},
    {"name": "BNB", "szDecimals": 3, "maxLeverage": 50},
    {"name": "APE", "szDecimals": 1, "maxLeverage": 50},
    {"name": "OP", "szDecimals": 1, "maxLeverage": 50},
    {"name": "LTC", "szDecimals": 2, "maxLeverage": 50},
    {"name": "ARB", "szDecimals": 1, "maxLeverage": 50},
    {"name": "DOGE", "szDecimals": 0, "maxLeverage": 50},
    {"name": "INJ", "szDecimals": 1, "maxLeverage": 50},
    {"name": "SUI", "szDecimals": 1, "maxLeverage": 50},
    {"name": "kPEPE", "szDecimals": 0, "maxLeverage": 50},
    {"name": "CRV", "szDecimals": 1, "maxLeverage": 50},
    {"name": "LDO", "szDecimals": 1, "maxLeverage": 50},
    {"name": "LINK", "szDecimals": 1, "maxLeverage": 50},
    {"name": "STX", "szDecimals": 1, "maxLeverage": 50},
    {"name": "RNDR", "szDecimals": 1, "maxLeverage": 50},
    {"name": "CFX", "szDecimals": 0, "maxLeverage": 50},
    {"name": "FTM", "szDecimals": 0, "maxLeverage": 50},
    {"name": "GMX", "szDecimals": 2, "maxLeverage": 50},
    {"name": "SNX", "szDecimals": 1, "maxLeverage": 50},
    {"name": "XRP", "szDecimals": 0, "maxLeverage": 50},
    {"name": "BCH", "szDecimals": 3, "maxLeverage": 50},
    {"name": "APT", "szDecimals": 2, "maxLeverage": 50},
]

_FAKE_RESPONSES: Dict[str, Any] = {
    "meta": {"universe": _META_UNIVERSE},
    "clearinghouseState": {
        "assetPositions": [{"position": {"coin": f"ASSET{i}"}} for i in range(12)],
        "marginSummary": {"accountValue": "1182.312496"},
        "crossMarginSummary": {"accountValue": "1182.312496"},
        "withdrawable": "1010.57173",
    },
    "openOrders": [{"oid": idx, "coin": "BTC", "sz": "1"} for idx in range(196)],
    "frontendOpenOrders": [
        {
            "coin": "BTC",
            "children": [],
            "limitPx": "10000",
            "sz": "1",
            "side": "A",
            "timestamp": 0,
        },
        {
            "coin": "ETH",
            "children": [],
            "limitPx": "2000",
            "sz": "2",
            "side": "B",
            "timestamp": 1,
        },
        {
            "coin": "ATOM",
            "children": [],
            "limitPx": "10",
            "sz": "3",
            "side": "A",
            "timestamp": 2,
        },
    ],
    "allMids": {"BTC": "10000", "ETH": "2000", "ATOM": "10", "MATIC": "1"},
    "userFills": [
        {"coin": "BTC", "px": "10000", "sz": "1", "side": "B", "time": 0, "crossed": True},
        {"coin": "ETH", "px": "2000", "sz": "2", "side": "A", "time": 1, "crossed": False},
    ],
    "userFillsByTime": [
        {"coin": "BTC", "px": "10000", "sz": "1", "side": "B", "time": idx}
        for idx in range(500)
    ],
    "fundingHistory": [
        {"coin": "BTC", "fundingRate": "0.001", "premium": "0.002", "time": 1681923833000}
    ],
    "l2Snapshot": {
        "coin": "DYDX",
        "time": 1684702007000,
        "levels": [
            [{"n": 1, "sz": "1.0", "px": "10.0"}],
            [{"n": 1, "sz": "1.0", "px": "9.5"}],
        ],
    },
    "candlesSnapshot": [
        {
            "T": 1684702007000 + i * 60000,
            "c": "10.0",
            "h": "10.5",
            "i": "1h",
            "l": "9.5",
            "n": 1,
            "o": "9.9",
            "s": "complete",
            "t": 1684702007000 + i * 60000,
            "v": "100",
        }
        for i in range(24)
    ],
    "userFundingHistory": [
        {
            "delta": {
                "coin": "BTC",
                "fundingRate": "0.001",
                "szi": "1",
                "type": "funding",
                "usdc": "10",
            },
            "hash": "0xabc",
            "time": 1681923833000,
        }
    ],
    "historicalOrders": [
        {
            "order": {"coin": "BTC", "sz": "1"},
            "status": "filled",
            "statusTimestamp": 1681923833000,
        }
    ],
    "userNonFundingLedgerUpdates": [
        {
            "delta": {
                "coin": "BTC",
                "fundingRate": "0.0",
                "szi": "0",
                "type": "rebate",
                "usdc": "1",
            },
            "hash": "0xdef",
            "time": 1681923833000,
        }
    ],
    "portfolio": [["24h", {"accountValueHistory": ["100"], "pnlHistory": ["1"], "vlm": ["50"]}]],
    "userTwapSliceFills": [
        {"coin": "ETH", "px": "2000", "sz": "1", "side": "B", "time": 1681923833000}
    ],
    "userVaultEquities": [
        {"vaultAddress": "0xVault", "equity": "1000", "vaultName": "Example Vault"}
    ],
    "userRole": {"role": "trader", "type": "standard"},
    "userRateLimit": {"limit": 1200, "window": "1m"},
    "delegatorHistory": [
        {"delta": {"coin": "ETH", "amount": "1"}, "hash": "0x123", "time": 1681923833000}
    ],
    "extraAgents": [
        {"name": "Example Agent", "address": "0xAgent", "validUntil": 1893456000}
    ],
}

_FAKE_RESPONSES["perpDexs"] = [
    {"name": "", "description": "core"},
    {
        "name": "solarak1n",
        "builder": {
            "address": "0x1111111111111111111111111111111111111111",
            "code": "SOLARA",
            "shareBps": "25",
        },
    },
    {
        "name": "keeper_f303",
        "builderAddress": "0x2222222222222222222222222222222222222222",
        "builderCode": "F303",
        "feeShareBps": 40,
    },
    {
        "name": "atlas_core",
        "builder": {
            "addr": "0x3333333333333333333333333333333333333333",
            "referralCode": "ATLAS",
            "bps": "12",
        },
    },
    {
        "name": "orphan",
        "description": "missing builder data",
    },
]

_FAKE_RESPONSES["l2Book"] = _FAKE_RESPONSES["l2Snapshot"]
_FAKE_RESPONSES["candleSnapshot"] = _FAKE_RESPONSES["candlesSnapshot"]
_FAKE_RESPONSES["userFunding"] = _FAKE_RESPONSES["userFundingHistory"]


def get_response(payload: Dict[str, Any]) -> Any:
    """Return a deep copy of the canned response for the provided payload."""
    payload_type = payload.get("type")
    if payload_type is None:
        raise ValueError("Payload is missing a 'type' field.")
    try:
        response = _FAKE_RESPONSES[payload_type]
    except KeyError as exc:  # pragma: no cover - keeps debugging context if new calls appear
        raise KeyError(f"No fake response registered for payload type {payload_type!r}.") from exc
    return deepcopy(response)
