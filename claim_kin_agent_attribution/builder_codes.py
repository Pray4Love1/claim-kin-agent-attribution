"""Utilities for extracting builder referral codes from Hyperliquid metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from hyperliquid.info import Info


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _normalise_address(value: str) -> Optional[str]:
    text = value.strip()
    if not text:
        return None
    if not text.startswith("0x"):
        text = f"0x{text}"
    text = text.lower()
    if len(text) != 42:
        return None
    return text


def _parse_share(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if not text:
            return None
        multiplier = 1
        if text.endswith("%"):
            multiplier = 100
            text = text[:-1]
        elif text.endswith("bps"):
            text = text[:-3]
        try:
            share = float(text)
        except ValueError:
            return None
        return int(round(share * multiplier))
    return None


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _coerce_entries(payload: Any) -> List[Mapping[str, Any]]:
    if isinstance(payload, Mapping):
        candidates: List[Mapping[str, Any]] = []
        for key in ("perpDexs", "dexs", "result", "data", "items", "payload"):
            if key in payload:
                nested = _coerce_entries(payload[key])
                if nested:
                    candidates.extend(nested)
        if candidates:
            return candidates
        if any(key in payload for key in ("builder", "builderAddress", "builder_code")):
            return [payload]
        return []
    if _is_sequence(payload):
        entries: List[Mapping[str, Any]] = []
        for item in payload:
            if isinstance(item, Mapping):
                entries.append(item)
            elif _is_sequence(item):
                entries.extend(_coerce_entries(item))
        return entries
    return []


def _extract_code(entry: Mapping[str, Any]) -> tuple[Optional[str], Optional[str], Optional[int]]:
    builder_info = _as_mapping(entry.get("builder"))
    address_candidates = (
        entry.get("builderAddress"),
        entry.get("builder_address"),
        builder_info.get("address"),
        builder_info.get("addr"),
        builder_info.get("builderAddress"),
    )
    address: Optional[str] = None
    for candidate in address_candidates:
        if isinstance(candidate, str):
            address = _normalise_address(candidate)
            if address:
                break

    if not address:
        return None, None, None

    code_candidates = (
        entry.get("builderCode"),
        entry.get("builder_code"),
        builder_info.get("code"),
        builder_info.get("referralCode"),
        builder_info.get("id"),
    )
    code: Optional[str] = None
    for candidate in code_candidates:
        if isinstance(candidate, str) and candidate.strip():
            code = candidate.strip()
            break

    share_candidates = (
        entry.get("feeShareBps"),
        entry.get("builderShareBps"),
        entry.get("shareBps"),
        builder_info.get("shareBps"),
        builder_info.get("bps"),
    )
    share: Optional[int] = None
    for candidate in share_candidates:
        share = _parse_share(candidate)
        if share is not None:
            break

    return address, code, share


def _coerce_name(entry: Mapping[str, Any], index: int) -> str:
    name_fields = (
        entry.get("name"),
        entry.get("dex"),
        entry.get("id"),
    )
    for field in name_fields:
        if isinstance(field, str) and field.strip():
            return field.strip()
    return f"builder_{index}"


@dataclass(frozen=True)
class BuilderCode:
    """Description of a builder referral configuration."""

    dex: str
    builder_address: str
    code: Optional[str] = None
    share_bps: Optional[int] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> MutableMapping[str, Any]:
        payload: MutableMapping[str, Any] = {
            "dex": self.dex,
            "builder_address": self.builder_address,
        }
        if self.code is not None:
            payload["code"] = self.code
        if self.share_bps is not None:
            payload["share_bps"] = self.share_bps
        payload["metadata"] = dict(self.metadata)
        return payload


def parse_builder_codes(payload: Any) -> List[BuilderCode]:
    entries = _coerce_entries(payload)
    results: List[BuilderCode] = []
    for index, entry in enumerate(entries):
        address, code, share = _extract_code(entry)
        if not address:
            continue
        dex = _coerce_name(entry, index)
        metadata: Mapping[str, Any] = dict(entry)
        results.append(
            BuilderCode(
                dex=dex,
                builder_address=address,
                code=code,
                share_bps=share,
                metadata=metadata,
            )
        )
    return results


def fetch_builder_codes(info: Info) -> List[BuilderCode]:
    """Fetch builder referral codes for the configured Hyperliquid instance."""

    payload = info.perp_dexs()
    codes = parse_builder_codes(payload)
    return codes


def filter_builder_codes(codes: Iterable[BuilderCode], addresses: Iterable[str]) -> List[BuilderCode]:
    normalised = {_normalise_address(addr) for addr in addresses if isinstance(addr, str)}
    normalised = {addr for addr in normalised if addr}
    if not normalised:
        return list(codes)
    return [code for code in codes if code.builder_address in normalised]
