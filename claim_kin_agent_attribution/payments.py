"""Utilities for extracting USD payment settlements from Hyperliquid ledger data."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, List, Optional


@dataclass(frozen=True)
class PaymentSettlement:
    """Represents a single ledger movement expressed in USD."""

    time_ms: int
    tx_hash: str
    kind: str
    amount_usd: Decimal
    direction: str
    metadata: dict[str, Any]

    @property
    def timestamp(self) -> datetime:
        """Return the UTC timestamp for the settlement."""

        return datetime.fromtimestamp(self.time_ms / 1000, tz=timezone.utc)

    def as_dict(self) -> dict[str, Any]:
        """Serialise the settlement to a JSON-friendly dictionary."""

        return {
            "time_ms": self.time_ms,
            "timestamp": self.timestamp.isoformat(),
            "tx_hash": self.tx_hash,
            "kind": self.kind,
            "amount_usd": str(self.amount_usd),
            "direction": self.direction,
            "metadata": self.metadata,
        }


def _as_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, "", "NaN"):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _extract_amount_from_delta(delta: dict[str, Any]) -> Optional[Decimal]:
    """Extract the USD amount represented by a ledger delta."""

    delta_type = delta.get("type", "")
    if "usdc" in delta and delta_type != "spotTransfer":
        amount = _as_decimal(delta.get("usdc"))
        return amount

    if delta_type == "spotTransfer":
        amount = _as_decimal(delta.get("usdcValue") or delta.get("amount"))
        if amount is None:
            return None
        fee = _as_decimal(delta.get("fee")) or Decimal("0")
        native_fee = _as_decimal(delta.get("nativeTokenFee")) or Decimal("0")
        direction_multiplier = Decimal("-1") if delta.get("destination") else Decimal("1")
        total = direction_multiplier * amount
        total += direction_multiplier * fee
        total += direction_multiplier * native_fee
        return total

    return None


def extract_payment_settlements(updates: Iterable[dict[str, Any]]) -> List[PaymentSettlement]:
    """Convert Hyperliquid ledger updates into signed USD settlements.

    Args:
        updates: Iterable of ledger update records from
            ``Info.user_non_funding_ledger_updates``.

    Returns:
        A list of :class:`PaymentSettlement` entries sorted by timestamp.
    """

    settlements: List[PaymentSettlement] = []
    for entry in updates:
        if not isinstance(entry, dict):
            continue
        delta = entry.get("delta")
        if not isinstance(delta, dict):
            continue
        amount = _extract_amount_from_delta(delta)
        if amount is None or amount == 0:
            continue
        direction = "credit" if amount > 0 else "debit"
        settlements.append(
            PaymentSettlement(
                time_ms=int(entry.get("time", 0)),
                tx_hash=str(entry.get("hash", "")),
                kind=str(delta.get("type", "unknown")),
                amount_usd=amount,
                direction=direction,
                metadata=delta,
            )
        )

    settlements.sort(key=lambda settlement: settlement.time_ms)
    return settlements


def total_settlement_amount(settlements: Iterable[PaymentSettlement]) -> Decimal:
    """Compute the net USD effect of a collection of settlements."""

    total = Decimal("0")
    for settlement in settlements:
        total += settlement.amount_usd
    return total
