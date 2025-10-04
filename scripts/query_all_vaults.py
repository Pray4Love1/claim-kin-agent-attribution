#!/usr/bin/env python3
"""Inspect vault balances and attribution metadata for known addresses."""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence, TYPE_CHECKING

try:  # pragma: no cover - import guard exercised indirectly in tests
    from web3 import Web3  # type: ignore[import]
    _WEB3_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - triggered in minimal environments
    Web3 = None  # type: ignore[assignment]
    _WEB3_AVAILABLE = False

if TYPE_CHECKING:  # pragma: no cover - type checking aid
    from web3.contract import Contract
else:  # pragma: no cover - runtime fallback when web3 is absent
    Contract = Any  # type: ignore[assignment]

DEFAULT_ADDRESSES: tuple[str, ...] = (
    "0xb2b297eF9449aa0905bC318B3bd258c4804BAd98",
    "0x996994D2914DF4eEE6176FD5eE152e2922787EE7",
)

DEFAULT_ABI_PATH = Path("artifacts/VaultScannerV2WithSig.abi.json")
DEFAULT_METHOD_CANDIDATES: tuple[str, ...] = (
    "queryVaultsForOwners",
    "getVaultsForOwners",
    "getVaults",
    "scanVaults",
    "scan",
)


class VaultScannerError(RuntimeError):
    """Raised when the vault scanner invocation cannot be satisfied."""


@dataclass
class VaultEntry:
    owner: str
    vault: str
    balance: int
    attribution_hash: str | None
    updated_at: int | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "vault": self.vault,
            "balance": str(self.balance),
            "attribution_hash": self.attribution_hash,
            "updated_at": self.updated_at,
        }


def _load_abi(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise VaultScannerError(f"ABI file not found at {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:  # pragma: no cover - exercised via tests
        raise VaultScannerError(f"Failed to parse ABI JSON at {path}") from exc


def _connect_web3(rpc_url: str) -> "Web3":
    if not _WEB3_AVAILABLE:
        raise VaultScannerError(
            "web3.py is required to query the vault scanner. Install it with `pip install web3`."
        )
    provider = Web3.HTTPProvider(rpc_url)  # type: ignore[arg-type]
    web3 = Web3(provider)
    if not web3.is_connected():  # pragma: no cover - requires live RPC
        raise VaultScannerError(f"Unable to connect to RPC endpoint {rpc_url}")
    return web3


def _resolve_method(contract: Contract, explicit: str | None) -> str:
    if explicit:
        if hasattr(contract.functions, explicit):
            return explicit
        raise VaultScannerError(f"Contract does not expose function {explicit}")

    for candidate in DEFAULT_METHOD_CANDIDATES:
        if hasattr(contract.functions, candidate):
            return candidate
    raise VaultScannerError(
        "Unable to determine scanner method automatically; "
        "specify one via --method or VAULT_SCANNER_METHOD."
    )


def _ensure_iterable(item: Any) -> Iterable[Any]:
    if isinstance(item, (list, tuple)):
        return item
    return (item,)


def _as_checksum(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        value = "0x" + value.hex()
    if isinstance(value, str):
        if not value.startswith("0x"):
            value = "0x" + value
        if _WEB3_AVAILABLE:
            return Web3.to_checksum_address(value)  # type: ignore[union-attr]
        if len(value) != 42:
            raise VaultScannerError(f"Address has unexpected length: {value!r}")
        return value.lower()
    raise VaultScannerError(f"Expected address-like value, received {value!r}")


def _as_hex(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (bytes, bytearray)):
        return "0x" + value.hex()
    if isinstance(value, str):
        return value if value.startswith("0x") else "0x" + value
    if isinstance(value, int):
        return hex(value)
    raise VaultScannerError(f"Unexpected hash payload {value!r}")


def _as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise VaultScannerError(f"Expected integer-compatible value, received {value!r}")


def _zip_components(owner: str, components: Sequence[Any]) -> list[VaultEntry]:
    if len(components) != 4:
        raise VaultScannerError(
            "Expected four components (vaults, balances, attribution hashes, timestamps)"
        )

    vaults, balances, attributions, timestamps = components
    entries: list[VaultEntry] = []
    for vault, balance, attribution, timestamp in zip(
        _ensure_iterable(vaults),
        _ensure_iterable(balances),
        _ensure_iterable(attributions),
        _ensure_iterable(timestamps),
    ):
        entries.append(
            VaultEntry(
                owner=owner,
                vault=_as_checksum(vault),
                balance=_as_int(balance),
                attribution_hash=_as_hex(attribution),
                updated_at=_as_int(timestamp),
            )
        )
    return entries


def _normalise_owner_payload(owner: str, payload: Any) -> list[VaultEntry]:
    if payload in (None, [], ()):  # no vaults
        return []

    if isinstance(payload, dict):
        if {"vaults", "balances", "attributionHashes", "timestamps"}.issubset(payload.keys()):
            return _zip_components(
                owner,
                (
                    payload["vaults"],
                    payload["balances"],
                    payload["attributionHashes"],
                    payload["timestamps"],
                ),
            )
        if "entries" in payload:
            return _normalise_owner_payload(owner, payload["entries"])

    if isinstance(payload, (list, tuple)):
        if payload and isinstance(payload[0], (list, tuple)) and len(payload[0]) >= 4:
            entries = []
            for entry in payload:
                vault, balance, attribution, timestamp, *_rest = list(entry) + [None, None]
                entries.append(
                    VaultEntry(
                        owner=owner,
                        vault=_as_checksum(vault),
                        balance=_as_int(balance),
                        attribution_hash=_as_hex(attribution),
                        updated_at=_as_int(timestamp),
                    )
                )
            return entries

        if len(payload) == 4:
            return _zip_components(owner, payload)

    raise VaultScannerError(f"Unrecognised payload format for owner {owner}: {payload!r}")


def _call_scanner(contract: Contract, method_name: str, owners: Sequence[str]) -> dict[str, Any]:
    function = getattr(contract.functions, method_name)

    try:
        return function(list(owners)).call()
    except (TypeError, ValueError):
        results: dict[str, Any] = {}
        for owner in owners:
            results[owner] = function(owner).call()
        return results


def _collect_entries(contract: Contract, method_name: str, owners: Sequence[str]) -> list[VaultEntry]:
    raw_response = _call_scanner(contract, method_name, owners)

    entries: list[VaultEntry] = []

    if isinstance(raw_response, dict):
        for owner, payload in raw_response.items():
            entries.extend(_normalise_owner_payload(owner, payload))
        return entries

    if isinstance(raw_response, (list, tuple)):
        if len(raw_response) == len(owners):
            for owner, payload in zip(owners, raw_response):
                entries.extend(_normalise_owner_payload(owner, payload))
            return entries

        if len(raw_response) == 4:
            # Assume components are shared across owners, fall back to first owner mapping
            entries.extend(_zip_components(owners[0], raw_response))
            return entries

    raise VaultScannerError(f"Unsupported response from scanner: {raw_response!r}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect vault balances and attribution metadata")
    parser.add_argument(
        "--rpc",
        default=os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
        help="Base RPC endpoint (defaults to BASE_RPC_URL or mainnet public RPC)",
    )
    parser.add_argument(
        "--contract",
        default=os.getenv("VAULT_SCANNER_ADDRESS"),
        required=os.getenv("VAULT_SCANNER_ADDRESS") is None,
        help="VaultScannerV2WithSig contract address",
    )
    parser.add_argument(
        "--abi",
        type=Path,
        default=Path(os.getenv("VAULT_SCANNER_ABI", str(DEFAULT_ABI_PATH))),
        help="Path to the VaultScanner ABI JSON (defaults to artifacts/VaultScannerV2WithSig.abi.json)",
    )
    parser.add_argument(
        "--method",
        default=os.getenv("VAULT_SCANNER_METHOD"),
        help="Contract view to call (autodetected when omitted)",
    )
    parser.add_argument(
        "--owner",
        action="append",
        dest="owners",
        help="Owner address to inspect (can be repeated). Defaults to the two known Codex addresses.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a table",
    )
    return parser


def _format_entries(entries: Sequence[VaultEntry]) -> str:
    if not entries:
        return "No vault positions discovered."

    header = f"{'Owner':42} {'Vault':42} {'Balance':>18} {'Attribution Hash':66} {'Updated At':>12}"
    lines = [header, "-" * len(header)]
    for entry in entries:
        lines.append(
            f"{entry.owner:42} {entry.vault:42} {entry.balance:18} "
            f"{(entry.attribution_hash or '—'):66} {entry.updated_at or 0:12}"
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    owners: tuple[str, ...]
    if args.owners:
        owners = tuple(_as_checksum(addr) for addr in args.owners)
    else:
        owners = tuple(_as_checksum(addr) for addr in DEFAULT_ADDRESSES)

    abi = _load_abi(args.abi)
    web3 = _connect_web3(args.rpc)
    contract = web3.eth.contract(
        address=_as_checksum(args.contract),
        abi=abi,
    )

    method_name = _resolve_method(contract, args.method)
    entries = _collect_entries(contract, method_name, owners)

    if args.json:
        payload = [entry.as_dict() for entry in entries]
        json.dump(payload, fp=os.sys.stdout, indent=2)
        os.sys.stdout.write("\n")
        return 0

    print(_format_entries(entries))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
