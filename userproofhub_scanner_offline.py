"""Offline-friendly scanner for unauthorized UserProofHub usage.

This module focuses on pulling already-known contract addresses from the
Etherscan-style explorers (Snowtrace, Arbscan, etc.) instead of executing wide
text searches like :mod:`scan_user_proof_hub`.  Security response teams often
receive curated address lists from partners, so the script optimises for that
workflow: it accepts addresses via command line flags, newline-separated files,
or JSON blobs and collects a concise indicator report for each contract.

Example usage::

    python userproofhub_scanner_offline.py \
        --address ethereum:0x1234... --address-file avalanche:contracts.txt \
        --api-key ethereum:MYKEY --output findings.json

The script stores the merged findings in ``findings_userproofhub.json`` by
default and prints a terse scan log to standard output.  Each finding contains
matched selectors, events, keywords, and selected explorer metadata.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional

try:  # pragma: no cover - optional dependency for runtime usage
    import requests  # type: ignore[assignment]
except ImportError:  # pragma: no cover - handled dynamically
    requests = None  # type: ignore[assignment]

# Public selectors, events, and keywords that have been associated with the
# stolen Zendity / Ava Labs UserProofHub logic across multiple reports.
MATCH_SELECTORS = [
    "verify(address,bytes32)",
    "sendCrossChainMessage(address,bytes)",
    "userProofHashes(address)",
    "isUserVerified(address)",
]

MATCH_EVENTS = ["ProofVerified(address,bytes32,uint256)"]

KEYWORDS = ["UserProofHub", "ITeleporterMessenger", "SPDX: Ecosystem", "Zendity", "Ava Labs"]

DEFAULT_BASE_URLS: Dict[str, str] = {
    "ethereum": "https://api.etherscan.io/api",
    "avalanche": "https://api.snowtrace.io/api",
    "base": "https://api.basescan.org/api",
    "arbitrum": "https://api.arbiscan.io/api",
    "optimism": "https://api-optimistic.etherscan.io/api",
    "polygon": "https://api.polygonscan.com/api",
    "sei": "https://sei-evm.blockscout.com/api",
}


class ExplorerError(RuntimeError):
    """Raised when an explorer API returns an unexpected response."""


def get_source_code(address: str, base_url: str, api_key: Optional[str] = None, *, timeout: int = 15) -> Mapping[str, str]:
    """Fetch a contract's verified source payload from an explorer."""

    if requests is None:  # pragma: no cover - executed only without dependency installed
        raise ImportError("The 'requests' package is required to query explorers.")

    params = {"module": "contract", "action": "getsourcecode", "address": address}
    if api_key:
        params["apikey"] = api_key
    try:
        response = requests.get(base_url, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - network failure
        raise ExplorerError(f"Error fetching source for {address} from {base_url}: {exc}") from exc

    payload = response.json()
    result = payload.get("result", [])
    if not isinstance(result, list) or not result:
        return {}
    entry = result[0]
    if not isinstance(entry, dict):
        raise ExplorerError(f"Unexpected response structure for {address}: {entry!r}")
    return entry


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    """Configure CLI arguments for offline scanning."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--address",
        action="append",
        help="Specific address to scan, formatted as chain:0x...",
    )
    parser.add_argument(
        "--address-file",
        action="append",
        help="File containing newline-separated addresses, formatted as chain:path",
    )
    parser.add_argument(
        "--address-json",
        help="JSON file with {chain: [addresses]} structure",
    )
    parser.add_argument(
        "--api-key",
        action="append",
        help="Explorer API key mapping formatted as chain:key",
    )
    parser.add_argument(
        "--base-url",
        action="append",
        help="Override the default explorer base URL via chain:url",
    )
    parser.add_argument(
        "--include-non-matches",
        action="store_true",
        help="Include addresses even if they do not match indicators",
    )
    parser.add_argument(
        "--output",
        default="findings_userproofhub.json",
        help="Destination JSON file for the findings",
    )
    return parser.parse_args(argv)


def _split_mapping_entries(entries: Optional[Iterable[str]]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not entries:
        return mapping
    for entry in entries:
        try:
            chain, value = entry.split(":", maxsplit=1)
        except ValueError as exc:  # pragma: no cover - defensive programming
            raise ExplorerError(f"Invalid mapping entry '{entry}'. Expected format chain:value.") from exc
        mapping[chain.strip()] = value.strip()
    return mapping


def _load_addresses_from_file(file_path: Path) -> List[str]:
    with file_path.open("r", encoding="utf-8") as handle:
        return [line.strip().lower() for line in handle if line.strip()]


def build_inputs(args: argparse.Namespace) -> Dict[str, List[str]]:
    """Aggregate addresses from CLI flags, files, and JSON blobs."""

    chains: Dict[str, List[str]] = {}
    if args.address:
        for entry in args.address:
            chain, address = entry.split(":", maxsplit=1)
            chains.setdefault(chain.strip(), []).append(address.strip().lower())

    if args.address_file:
        for entry in args.address_file:
            chain, file_name = entry.split(":", maxsplit=1)
            addresses = _load_addresses_from_file(Path(file_name))
            chains.setdefault(chain.strip(), []).extend(addresses)

    if args.address_json:
        with Path(args.address_json).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        for chain, address_list in payload.items():
            chains.setdefault(chain, []).extend(addr.lower() for addr in address_list)

    # Deduplicate addresses within each chain while preserving order.
    for chain, addresses in chains.items():
        seen: Dict[str, None] = {}
        deduped: List[str] = []
        for addr in addresses:
            if addr not in seen:
                seen[addr] = None
                deduped.append(addr)
        chains[chain] = deduped
    return chains


def analyse_source(source: str) -> Dict[str, object]:
    """Return indicator matches for a verified source string."""

    selectors: List[str] = []
    events: List[str] = []
    keywords: List[str] = []

    for signature in MATCH_SELECTORS:
        if signature.split("(")[0] in source:
            selectors.append(signature)

    for event_signature in MATCH_EVENTS:
        event_name = event_signature.split("(")[0]
        if event_name in source:
            events.append(event_signature)

    for keyword in KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", source, flags=re.IGNORECASE):
            keywords.append(keyword)

    matched = bool(selectors or events or keywords)
    return {
        "selectors": selectors,
        "events": events,
        "keywords": keywords,
        "matched": matched,
    }


def scan(args: argparse.Namespace) -> List[Dict[str, object]]:
    """Execute the offline scan and return the finding list."""

    chains = build_inputs(args)
    api_keys = _split_mapping_entries(args.api_key)
    base_urls: MutableMapping[str, str] = dict(DEFAULT_BASE_URLS)
    base_urls.update(_split_mapping_entries(args.base_url))

    findings: List[Dict[str, object]] = []
    for chain, addresses in chains.items():
        if chain not in base_urls:
            raise ExplorerError(f"No base URL configured for chain '{chain}'.")
        base_url = base_urls[chain]
        api_key = api_keys.get(chain)
        for address in addresses:
            print(f"🔍 Scanning {chain}:{address}...")
            payload = get_source_code(address, base_url, api_key)
            source_blob = payload.get("SourceCode", "")
            if not source_blob:
                if args.include_non_matches:
                    findings.append(
                        {
                            "address": address,
                            "chain": chain,
                            "contractName": payload.get("ContractName"),
                            "compilerVersion": payload.get("CompilerVersion"),
                            "proxy": payload.get("Proxy"),
                            "implementation": payload.get("Implementation"),
                            "sourceLastVerified": payload.get("LastVerified"),
                            "indicators": {"selectors": [], "events": [], "keywords": [], "matched": False},
                        }
                    )
                continue

            if isinstance(source_blob, (dict, list)):
                source_text = json.dumps(source_blob)
            else:
                source_text = source_blob

            indicators = analyse_source(source_text)
            if indicators["matched"] or args.include_non_matches:
                findings.append(
                    {
                        "address": address,
                        "chain": chain,
                        "contractName": payload.get("ContractName"),
                        "compilerVersion": payload.get("CompilerVersion"),
                        "proxy": payload.get("Proxy"),
                        "implementation": payload.get("Implementation"),
                        "sourceLastVerified": payload.get("LastVerified"),
                        "indicators": indicators,
                    }
                )

    output_path = Path(args.output)
    output_path.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"\n✅ Done. {len(findings)} contract(s) saved to {output_path}")
    return findings


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    scan(args)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
