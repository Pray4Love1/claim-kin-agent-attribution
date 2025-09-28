#!/usr/bin/env python3
"""Scan verified contracts for stolen UserProofHub logic."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Sequence, Set

try:  # pragma: no cover - optional dependency for offline testing
    import requests  # type: ignore[assignment]
except ImportError:  # pragma: no cover - handled during runtime
    requests = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from eth_utils import keccak as _keccak  # type: ignore
except ImportError:  # pragma: no cover - handled during runtime
    _keccak = None

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from requests import Session  # noqa: F401

DEFAULT_TIMEOUT = 15
DEFAULT_PAGE_SIZE = 50

FUNCTION_SELECTORS = {
    "verify(address,bytes32)": "0xfbc7ef51",
    "getUserProofHash(address)": "0x8231cdd1",
    "isUserVerified(address)": "0x04e94d4a",
    "transportProof(address,bytes32,string)": "0x9a0a9d5c",
}

EVENT_TOPICS = {
    "ProofVerified(address,bytes32)": "0xfbc7ef51309bc49609dbecb8b5eb2ea253df61084a94895b62a4600605fdcfc8",
}

KEYWORDS = [
    "userProofHashes",
    "ProofVerified",
    "ITeleporterMessenger",
    "sendCrossChainMessage",
    "TeleporterMessageInput",
]

NETWORK_EXPLORERS = {
    "avalanche": {
        "base_url": "https://blockscout.com/avalanche/mainnet/api/v2",
        "display_url": "https://blockscout.com/avalanche/mainnet",
    },
    "ethereum": {
        "base_url": "https://blockscout.com/eth/mainnet/api/v2",
        "display_url": "https://blockscout.com/eth/mainnet",
    },
    "base": {
        "base_url": "https://base.blockscout.com/api/v2",
        "display_url": "https://base.blockscout.com",
    },
    "arbitrum": {
        "base_url": "https://blockscout.com/arbitrum/mainnet/api/v2",
        "display_url": "https://blockscout.com/arbitrum/mainnet",
    },
    "optimism": {
        "base_url": "https://optimism.blockscout.com/api/v2",
        "display_url": "https://optimism.blockscout.com",
    },
    "sei": {
        "base_url": "https://sei-evm.blockscout.com/api/v2",
        "display_url": "https://sei-evm.blockscout.com",
    },
}


class ExplorerError(RuntimeError):
    """Raised when an explorer API responds with an error."""


@dataclass
class ExplorerContract:
    address: str
    name: Optional[str]
    explorer_url: str
    abi: Optional[Sequence[dict]] = None
    source_text: str = ""


@dataclass
class ContractMatch:
    contract: ExplorerContract
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "address": self.contract.address,
            "name": self.contract.name,
            "explorer_url": self.contract.explorer_url,
            "reasons": self.reasons,
        }


class BlockscoutExplorer:
    """Thin wrapper around a Blockscout API instance."""

    def __init__(self, base_url: str, display_url: str, session: Optional["Session"] = None):
        if requests is None:  # pragma: no cover - exercised only when dependency missing
            raise ImportError("The 'requests' package is required to query explorers.")
        self.base_url = base_url.rstrip("/")
        self.display_url = display_url.rstrip("/")
        self.session = session or requests.Session()

    def _request(self, path: str, *, params: Optional[Dict[str, object]] = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
        url = f"{self.base_url}{path}"
        response = self.session.get(url, params=params, timeout=timeout)
        if response.status_code != 200:
            raise ExplorerError(
                f"Explorer returned HTTP {response.status_code} for {url}: {response.text[:200]}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise ExplorerError(f"Failed to decode JSON from {url}: {exc}") from exc

    def iter_text_search(
        self,
        query: str,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: Optional[int] = None,
    ) -> Iterator[dict]:
        page = 1
        pages_seen = 0
        while True:
            if max_pages is not None and pages_seen >= max_pages:
                break
            params = {
                "filter": "text_search",
                "query": query,
                "page": page,
                "page_size": page_size,
            }
            payload = self._request("/smart-contracts", params=params)
            items = payload.get("items", [])
            if not items:
                break
            for item in items:
                yield item
            if len(items) < page_size:
                break
            page += 1
            pages_seen += 1

    def fetch_contract(self, address: str) -> ExplorerContract:
        data = self._request(f"/smart-contracts/{address.lower()}")
        name = data.get("name")
        abi = _extract_abi(data)
        source_text = _extract_source_text(data)
        url = f"{self.display_url}/address/{address.lower()}"
        return ExplorerContract(address=address, name=name, abi=abi, source_text=source_text, explorer_url=url)


def _extract_abi(data: dict) -> Optional[Sequence[dict]]:
    abi = data.get("abi")
    if abi:
        return abi

    verified = data.get("verified_contract")
    if not verified:
        return None

    abi = verified.get("abi")
    if isinstance(abi, str):
        try:
            return json.loads(abi)
        except json.JSONDecodeError:
            return None
    return abi


def _extract_source_text(data: dict) -> str:
    sources: List[str] = []

    verified = data.get("verified_contract")
    if verified:
        source_field = verified.get("source") or verified.get("source_code")
        if isinstance(source_field, str):
            sources.append(source_field)
        elif isinstance(source_field, dict):
            for value in source_field.values():
                if isinstance(value, dict):
                    content = value.get("content") or value.get("source")
                    if isinstance(content, str):
                        sources.append(content)
                elif isinstance(value, str):
                    sources.append(value)

        sourcify_meta = verified.get("sourcify_metadata")
        if isinstance(sourcify_meta, dict):
            files = sourcify_meta.get("files")
            if isinstance(files, dict):
                for entry in files.values():
                    if isinstance(entry, dict):
                        content = entry.get("content")
                        if isinstance(content, str):
                            sources.append(content)

    top_sources = data.get("sources")
    if isinstance(top_sources, dict):
        for value in top_sources.values():
            if isinstance(value, dict):
                content = value.get("content") or value.get("source")
                if isinstance(content, str):
                    sources.append(content)
            elif isinstance(value, str):
                sources.append(value)

    return "\n".join(sources)


def _signature_from_abi_entry(entry: dict) -> Optional[str]:
    name = entry.get("name")
    if not name:
        return None
    inputs = entry.get("inputs", [])
    input_types = ",".join(param.get("type", "unknown") for param in inputs)
    return f"{name}({input_types})"


def compute_function_selectors(abi: Sequence[dict]) -> Dict[str, str]:
    selectors: Dict[str, str] = {}
    for entry in abi:
        if entry.get("type") != "function":
            continue
        signature = _signature_from_abi_entry(entry)
        if not signature:
            continue
        if signature in FUNCTION_SELECTORS:
            selectors[signature] = FUNCTION_SELECTORS[signature]
        elif _keccak:
            selectors[signature] = "0x" + _keccak(text=signature)[:4].hex()
    return selectors


def compute_event_topics(abi: Sequence[dict]) -> Dict[str, str]:
    topics: Dict[str, str] = {}
    for entry in abi:
        if entry.get("type") != "event":
            continue
        signature = _signature_from_abi_entry(entry)
        if not signature:
            continue
        if signature in EVENT_TOPICS:
            topics[signature] = EVENT_TOPICS[signature]
        elif _keccak:
            topics[signature] = "0x" + _keccak(text=signature).hex()
    return topics


def find_matches(contract: ExplorerContract) -> Optional[ContractMatch]:
    reasons: List[str] = []

    if contract.abi:
        selectors = compute_function_selectors(contract.abi)
        selector_hits = [
            sig for sig, selector in FUNCTION_SELECTORS.items() if selector in selectors.values()
        ]
        if selector_hits:
            reasons.append("Function selectors present: " + ", ".join(sorted(selector_hits)))

        topics = compute_event_topics(contract.abi)
        event_hits = [sig for sig, topic in EVENT_TOPICS.items() if topic in topics.values()]
        if event_hits:
            reasons.append("Events present: " + ", ".join(sorted(event_hits)))

    if contract.source_text:
        lowered = contract.source_text.lower()
        keyword_hits = [kw for kw in KEYWORDS if kw.lower() in lowered]
        if keyword_hits:
            reasons.append("Keywords present: " + ", ".join(sorted(keyword_hits)))

    if reasons:
        return ContractMatch(contract=contract, reasons=reasons)
    return None


def scan_network(
    explorer: BlockscoutExplorer,
    *,
    page_size: int,
    max_pages: Optional[int],
    indicators: Sequence[str],
) -> List[ContractMatch]:
    seen_addresses: Set[str] = set()
    matches: List[ContractMatch] = []

    for indicator in indicators:
        logging.info("Searching for '%s'", indicator)
        try:
            results = explorer.iter_text_search(indicator, page_size=page_size, max_pages=max_pages)
            for item in results:
                address = item.get("address_hash") or item.get("address") or item.get("address_hashes")
                if not address:
                    continue
                address = address.lower()
                if address in seen_addresses:
                    continue
                seen_addresses.add(address)
                try:
                    contract = explorer.fetch_contract(address)
                except ExplorerError as exc:
                    logging.warning("Failed to fetch contract %s: %s", address, exc)
                    continue

                match = find_matches(contract)
                if match:
                    matches.append(match)
        except ExplorerError as exc:
            logging.error("Explorer search failed for '%s': %s", indicator, exc)
    return matches


def collect_unique_addresses(matches_by_network: Dict[str, List[ContractMatch]]) -> List[str]:
    """Return a sorted, deduplicated list of contract addresses."""

    addresses = {
        match.contract.address.lower()
        for network_matches in matches_by_network.values()
        for match in network_matches
    }
    return sorted(addresses)


def build_proof_report(
    template: Dict[str, object],
    matches_by_network: Dict[str, List[ContractMatch]],
) -> Dict[str, object]:
    """Augment a proof overlap template with the collected matches."""

    report = deepcopy(template)
    addresses = collect_unique_addresses(matches_by_network)

    report["matching_addresses"] = addresses
    report["matching_contracts"] = [
        {
            "network": network,
            **match.to_dict(),
        }
        for network, network_matches in sorted(matches_by_network.items())
        for match in network_matches
    ]
    report["match_count"] = len(report["matching_contracts"])
    return report


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--network",
        choices=sorted(NETWORK_EXPLORERS.keys()),
        action="append",
        help="Restrict scanning to one or more specific networks.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to fetch per indicator (default: all available).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help="Number of contracts to request per page (default: %(default)s).",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Write JSON results to the given path in addition to stdout logging.",
    )
    parser.add_argument(
        "--addresses-output",
        type=str,
        help="Write newline-separated matching addresses to the specified file.",
    )
    parser.add_argument(
        "--proof-report-template",
        type=str,
        help=(
            "Path to a proof overlap report template JSON to augment with the matching"
            " contracts."
        ),
    )
    parser.add_argument(
        "--proof-report-output",
        type=str,
        help=(
            "Destination path for the augmented proof overlap report. Defaults to"
            " overwriting the template path."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    networks = args.network or list(NETWORK_EXPLORERS.keys())
    logging.info("Scanning %d network(s): %s", len(networks), ", ".join(networks))

    indicators: List[str] = list(FUNCTION_SELECTORS.values()) + list(EVENT_TOPICS.values()) + KEYWORDS

    all_matches: Dict[str, List[ContractMatch]] = {}

    for network in networks:
        config = NETWORK_EXPLORERS[network]
        explorer = BlockscoutExplorer(config["base_url"], config["display_url"])
        logging.info("=== %s ===", network)
        matches = scan_network(
            explorer,
            page_size=args.page_size,
            max_pages=args.max_pages,
            indicators=indicators,
        )
        if matches:
            all_matches[network] = matches
            for match in matches:
                logging.info(
                    "Match %s (%s): %s",
                    match.contract.address,
                    match.contract.name or "unknown",
                    "; ".join(match.reasons),
                )
        else:
            logging.info("No matches detected on %s", network)

    if args.output:
        serialised = {
            network: [match.to_dict() for match in matches]
            for network, matches in all_matches.items()
        }
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(serialised, handle, indent=2)
        logging.info("Saved results to %s", args.output)

    if args.addresses_output:
        addresses = collect_unique_addresses(all_matches)
        output_path = Path(args.addresses_output)
        output_path.write_text("\n".join(addresses) + ("\n" if addresses else ""), encoding="utf-8")
        logging.info("Saved %d address(es) to %s", len(addresses), output_path)

    if args.proof_report_template:
        template_path = Path(args.proof_report_template)
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        output_path = Path(args.proof_report_output or template_path)
        template_data = json.loads(template_path.read_text(encoding="utf-8"))
        report_data = build_proof_report(template_data, all_matches)
        output_path.write_text(json.dumps(report_data, indent=2) + "\n", encoding="utf-8")
        logging.info("Saved proof overlap report to %s", output_path)

    if not all_matches:
        logging.info("No matching contracts found across the selected networks.")
    else:
        logging.info(
            "Found %d matching contract(s) across %d network(s).",
            sum(len(matches) for matches in all_matches.values()),
            len(all_matches),
        )

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
