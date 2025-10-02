#!/usr/bin/env python3
"""Scan verified contracts for stolen UserProofHub logic.

This utility targets the Zendity/Ava Labs "UserProofHub" pattern by looking
for a constellation of markers:

* Specific function selectors associated with the stolen logic.
* Event signature hashes raised by the implementation.
* Textual keywords that frequently appear in copied source files.

The scanner walks the verified contract catalogue for several EVM networks and
records any contracts that exhibit these signals. The default configuration
covers Avalanche, Ethereum, Base, Arbitrum, Optimism, and Sei, but networks can
be limited via the command line.

Example usage::

    python scan_userproofhub.py --max-contracts 200 --output hits.json

The script speaks to public block explorer APIs (Blockscout and Routescan) and
therefore requires outbound internet access. When running inside restricted
sandboxes you may need to provide an HTTPS proxy via environment variables.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from eth_utils import keccak

SelectorSignature = Dict[str, str]
EventSignature = Dict[str, str]

SELECTOR_SIGNATURES: SelectorSignature = {
    "verify(address,bytes32)": "0xfbc7ef51",
    "getUserProofHash(address)": "0x8231cdd1",
    "isUserVerified(address)": "0x04e94d4a",
    "transportProof(address,bytes32,string)": "0x9a0a9d5c",
}

EVENT_SIGNATURES: EventSignature = {
    "ProofVerified(address,bytes32)": "0xfbc7ef51309bc49609dbecb8b5eb2ea253df61084a94895b62a4600605fdcfc8",
}

KEYWORDS: Sequence[str] = (
    "userProofHashes",
    "ProofVerified",
    "ITeleporterMessenger",
    "sendCrossChainMessage",
    "TeleporterMessageInput",
)

DEFAULT_NETWORKS: Sequence[str] = (
    "avalanche",
    "ethereum",
    "base",
    "arbitrum",
    "optimism",
    "sei",
)


@dataclass
class NetworkConfig:
    """Configuration for a supported block explorer."""

    name: str
    explorer_type: str  # "blockscout" or "routescan"
    base_url: str
    address_url_template: Optional[str] = None
    page_size: int = 50

    def address_url(self, address: str) -> Optional[str]:
        if self.address_url_template:
            return self.address_url_template.format(address=address)
        return None


ROUTESCAN_BASE = "https://api.routescan.io/v2/network/mainnet/evm"

NETWORK_CONFIGS: Dict[str, NetworkConfig] = {
    "avalanche": NetworkConfig(
        name="avalanche",
        explorer_type="routescan",
        base_url=f"{ROUTESCAN_BASE}/43114",
        address_url_template="https://routescan.io/mainnet/evm/43114/address/{address}",
        page_size=100,
    ),
    "ethereum": NetworkConfig(
        name="ethereum",
        explorer_type="blockscout",
        base_url="https://eth.blockscout.com",
        address_url_template="https://eth.blockscout.com/address/{address}",
        page_size=100,
    ),
    "base": NetworkConfig(
        name="base",
        explorer_type="blockscout",
        base_url="https://base.blockscout.com",
        address_url_template="https://base.blockscout.com/address/{address}",
        page_size=100,
    ),
    "arbitrum": NetworkConfig(
        name="arbitrum",
        explorer_type="blockscout",
        base_url="https://arbitrum.blockscout.com",
        address_url_template="https://arbitrum.blockscout.com/address/{address}",
        page_size=100,
    ),
    "optimism": NetworkConfig(
        name="optimism",
        explorer_type="blockscout",
        base_url="https://optimism.blockscout.com",
        address_url_template="https://optimism.blockscout.com/address/{address}",
        page_size=100,
    ),
    "sei": NetworkConfig(
        name="sei",
        explorer_type="routescan",
        base_url=f"{ROUTESCAN_BASE}/1329",
        address_url_template="https://routescan.io/mainnet/evm/1329/address/{address}",
        page_size=100,
    ),
}


class ExplorerError(RuntimeError):
    """Raised when an explorer request fails irrecoverably."""


def build_url(base: str, params: Optional[Dict[str, str]] = None) -> str:
    if not params:
        return base
    return f"{base}?{urlencode(params)}"


def fetch_json(
    url: str,
    params: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    retries: int = 3,
    retry_backoff: float = 1.8,
) -> Dict:
    """Fetch JSON with basic retry and exponential backoff."""

    attempt = 0
    while True:
        try:
            request = Request(build_url(url, params), headers=headers or {})
            with urlopen(request, timeout=timeout) as response:
                payload = response.read()
                encoding = response.headers.get_content_charset() or "utf-8"
                return json.loads(payload.decode(encoding))
        except HTTPError as exc:  # type: ignore[reportGeneralTypeIssues]
            status = exc.code
            if status in {429, 500, 502, 503, 504} and attempt < retries:
                sleep_for = retry_backoff ** attempt
                logging.debug(
                    "HTTP %s from %s, retrying in %.2fs", status, url, sleep_for
                )
                time.sleep(sleep_for)
                attempt += 1
                continue
            raise ExplorerError(f"{url} returned HTTP {status}") from exc
        except URLError as exc:
            if attempt < retries:
                sleep_for = retry_backoff ** attempt
                logging.debug(
                    "Network error '%s' from %s, retrying in %.2fs",
                    exc.reason,
                    url,
                    sleep_for,
                )
                time.sleep(sleep_for)
                attempt += 1
                continue
            raise ExplorerError(f"Failed to reach {url}: {exc.reason}") from exc
        except json.JSONDecodeError as exc:  # type: ignore[attr-defined]
            raise ExplorerError(f"Malformed JSON from {url}") from exc


def selector_for_signature(signature: str) -> str:
    selector = keccak(text=signature)[:4]
    return "0x" + selector.hex()


def event_hash_for_signature(signature: str) -> str:
    return "0x" + keccak(text=signature).hex()


SELECTOR_LOOKUP = {
    selector.lower(): signature for signature, selector in SELECTOR_SIGNATURES.items()
}
EVENT_LOOKUP = {
    event_hash.lower(): signature for signature, event_hash in EVENT_SIGNATURES.items()
}


@dataclass
class ContractSource:
    address: str
    contract_name: Optional[str]
    source_code: str
    abi: str
    explorer_url: Optional[str]
    metadata: Dict[str, str]


def parse_abi(abi_raw: str) -> List[Dict]:
    try:
        abi = json.loads(abi_raw)
        if isinstance(abi, list):
            return abi
    except json.JSONDecodeError:
        pass
    return []


def keyword_hits(text: str) -> List[str]:
    lowered = text.lower()
    return [keyword for keyword in KEYWORDS if keyword.lower() in lowered]


def analyze_contract(contract: ContractSource) -> Optional[Dict[str, object]]:
    abi_entries = parse_abi(contract.abi)
    function_hits: List[Dict[str, str]] = []
    event_hits: List[Dict[str, str]] = []

    for entry in abi_entries:
        if entry.get("type") == "function":
            name = entry.get("name")
            inputs = entry.get("inputs", [])
            if not name or not isinstance(inputs, list):
                continue
            try:
                signature = f"{name}({','.join(param['type'] for param in inputs)})"
            except KeyError:
                continue
            selector = selector_for_signature(signature)
            expected_signature = SELECTOR_LOOKUP.get(selector.lower())
            if expected_signature:
                function_hits.append(
                    {
                        "abi_signature": signature,
                        "selector": selector,
                        "expected_signature": expected_signature,
                    }
                )
        elif entry.get("type") == "event":
            name = entry.get("name")
            inputs = entry.get("inputs", [])
            if not name or not isinstance(inputs, list):
                continue
            try:
                signature = f"{name}({','.join(param['type'] for param in inputs)})"
            except KeyError:
                continue
            event_hash = event_hash_for_signature(signature)
            expected_signature = EVENT_LOOKUP.get(event_hash.lower())
            if expected_signature:
                event_hits.append(
                    {
                        "abi_signature": signature,
                        "event_hash": event_hash,
                        "expected_signature": expected_signature,
                    }
                )

    keyword_matches = keyword_hits(contract.source_code)
    if (
        not function_hits
        and not event_hits
        and not keyword_matches
        and not keyword_hits(contract.metadata.get("ContractName", ""))
    ):
        return None

    metadata_copy = {**contract.metadata}
    metadata_copy.pop("SourceCode", None)
    metadata_copy.pop("ABI", None)

    return {
        "address": contract.address,
        "contract_name": contract.contract_name,
        "explorer_url": contract.explorer_url,
        "function_hits": function_hits,
        "event_hits": event_hits,
        "keyword_hits": keyword_matches,
        "metadata": metadata_copy,
    }


def iter_blockscout_contracts(
    config: NetworkConfig,
    limit: Optional[int] = None,
    start_page: int = 1,
) -> Iterator[Dict[str, Optional[str]]]:
    page_params: Dict[str, str] = {"page": str(start_page), "page_size": str(config.page_size), "filter": "verified"}
    fetched = 0

    while True:
        url = f"{config.base_url}/api/v2/smart-contracts"
        response = fetch_json(url, params=page_params)
        items = response.get("items", [])
        if not items:
            return

        for item in items:
            address = item.get("address")
            if not address:
                continue
            yield {"address": address, "name": item.get("name")}
            fetched += 1
            if limit is not None and fetched >= limit:
                return

        next_page = response.get("next_page_params")
        if not next_page:
            return

        page_params = {key: str(value) for key, value in next_page.items()}


def iter_routescan_contracts(
    config: NetworkConfig,
    limit: Optional[int] = None,
    start_page: int = 1,
) -> Iterator[Dict[str, Optional[str]]]:
    fetched = 0
    page = start_page
    while True:
        url = f"{config.base_url}/contract/verified"
        params = {"page": str(page), "size": str(config.page_size)}
        response = fetch_json(url, params=params)
        items = response.get("items") or response.get("contracts") or response.get("data")
        if not items:
            return
        for item in items:
            address = item.get("address") or item.get("contractAddress") or item.get("contract_address")
            if not address:
                continue
            yield {"address": address, "name": item.get("name") or item.get("contractName")}
            fetched += 1
            if limit is not None and fetched >= limit:
                return
        total_pages = response.get("totalPages") or response.get("total_pages")
        if total_pages and page >= int(total_pages):
            return
        page += 1


def get_source_blockscout(config: NetworkConfig, address: str) -> Optional[ContractSource]:
    url = f"{config.base_url}/api"
    params = {"module": "contract", "action": "getsourcecode", "address": address}
    response = fetch_json(url, params=params)
    result = response.get("result") or []
    if not result:
        return None
    entry = result[0]
    source_code = entry.get("SourceCode", "")
    abi = entry.get("ABI", "[]")
    contract_name = entry.get("ContractName") or entry.get("contractName")
    metadata = {key: value for key, value in entry.items() if isinstance(value, str)}
    return ContractSource(
        address=address,
        contract_name=contract_name,
        source_code=source_code,
        abi=abi,
        explorer_url=config.address_url(address),
        metadata=metadata,
    )


def get_source_routescan(config: NetworkConfig, address: str) -> Optional[ContractSource]:
    url = f"{config.base_url}/etherscan/api"
    params = {"module": "contract", "action": "getsourcecode", "address": address}
    response = fetch_json(url, params=params)
    result = response.get("result") or []
    if not result:
        return None
    entry = result[0]
    source_code = entry.get("SourceCode", "")
    abi = entry.get("ABI", "[]")
    contract_name = entry.get("ContractName") or entry.get("contractName")
    metadata = {key: value for key, value in entry.items() if isinstance(value, str)}
    return ContractSource(
        address=address,
        contract_name=contract_name,
        source_code=source_code,
        abi=abi,
        explorer_url=config.address_url(address),
        metadata=metadata,
    )


def scan_network(
    config: NetworkConfig,
    limit: Optional[int] = None,
    start_page: int = 1,
    require_selectors: bool = False,
) -> List[Dict[str, object]]:
    logging.info("Scanning %s (limit=%s)", config.name, limit or "∞")

    if config.explorer_type == "blockscout":
        iterator = iter_blockscout_contracts(config, limit=limit, start_page=start_page)
        source_fetcher = get_source_blockscout
    elif config.explorer_type == "routescan":
        iterator = iter_routescan_contracts(config, limit=limit, start_page=start_page)
        source_fetcher = get_source_routescan
    else:
        raise ValueError(f"Unsupported explorer type: {config.explorer_type}")

    matches: List[Dict[str, object]] = []
    scanned = 0

    for contract_info in iterator:
        address = contract_info.get("address")
        if not address:
            continue
        scanned += 1
        try:
            source = source_fetcher(config, address)
        except ExplorerError as exc:
            logging.warning("%s: failed to fetch source for %s: %s", config.name, address, exc)
            continue
        if not source:
            continue
        result = analyze_contract(source)
        if not result:
            continue
        if require_selectors and not result.get("function_hits"):
            continue
        result["network"] = config.name
        matches.append(result)

    logging.info("Finished %s: scanned %d contracts, found %d matches", config.name, scanned, len(matches))
    return matches


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--networks",
        nargs="*",
        default=list(DEFAULT_NETWORKS),
        help="Subset of networks to scan (default: all supported)",
    )
    parser.add_argument(
        "--max-contracts",
        type=int,
        default=None,
        help="Maximum verified contracts to pull per network (default: unlimited)",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="Pagination starting point for explorer listings (default: 1)",
    )
    parser.add_argument(
        "--require-selectors",
        action="store_true",
        help="Only report matches that hit at least one function selector",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to dump the JSON report",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging verbosity (DEBUG, INFO, WARNING)",
    )
    return parser.parse_args(argv)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level)

    unknown_networks = [name for name in args.networks if name not in NETWORK_CONFIGS]
    if unknown_networks:
        logging.error("Unsupported networks requested: %s", ", ".join(unknown_networks))
        return 1

    aggregated: List[Dict[str, object]] = []
    for network_name in args.networks:
        config = NETWORK_CONFIGS[network_name]
        try:
            network_matches = scan_network(
                config,
                limit=args.max_contracts,
                start_page=args.start_page,
                require_selectors=args.require_selectors,
            )
        except ExplorerError as exc:
            logging.error("%s: explorer failure: %s", network_name, exc)
            continue
        aggregated.extend(network_matches)

    aggregated.sort(key=lambda item: (
        -(len(item.get("function_hits", [])) + len(item.get("event_hits", []))),
        -(len(item.get("keyword_hits", []))),
        item.get("address", ""),
    ))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            json.dump(aggregated, handle, indent=2)
        logging.info("Wrote report to %s", args.output)
    else:
        print(json.dumps(aggregated, indent=2))

    logging.info("Scan complete: %d total matches", len(aggregated))
    return 0


if __name__ == "__main__":
    sys.exit(main())
