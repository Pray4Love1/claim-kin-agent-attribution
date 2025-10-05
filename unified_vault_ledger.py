"""Utilities for normalising vault equity records into a unified ledger."""
from __future__ import annotations

from numbers import Number
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

# Keys observed across ledger-style payloads returned by different API surfaces.
_EQUITY_KEYS: Sequence[str] = (
    "equity",
    "vaultEquity",
    "aum",
    "assetsUnderManagement",
    "assetsUnderManagementUsd",
    "tvl",
)


def fetch_vault_equity(entries: Iterable[Mapping[str, Any]]) -> list[MutableMapping[str, Any]]:
    """Return ledger entries enriched with a unified ``equity`` field.

    The Hyperliquid APIs expose vault equity under a handful of different
    attribute names. Historically the lookup relied on a chained ``or``
    expression which inadvertently treated zero-equity balances (``0`` or
    ``0.0``) as missing values. This helper now performs explicit ``None``
    filtering so the zero values persist in the resulting ledger while still
    falling back through the other aliases when appropriate.
    """

    def _match_entry(entry: Mapping[str, Any], keys: Sequence[str]) -> Any:
        for key in keys:
            if key not in entry:
                continue
            value = entry[key]
            if value is None:
                continue
            if isinstance(value, bool):
                if value:
                    return value
                continue
            if isinstance(value, Number):
                return value
            if value:
                return value
        return None

    ledger: list[MutableMapping[str, Any]] = []
    for entry in entries:
        normalised: MutableMapping[str, Any] = dict(entry)
        normalised["equity"] = _match_entry(entry, _EQUITY_KEYS)
        ledger.append(normalised)
    return ledger
