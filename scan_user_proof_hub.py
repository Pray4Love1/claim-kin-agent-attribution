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

try:
    import requests
except ImportError:
    requests = None

try:
    from eth_utils import keccak as _keccak
except ImportError:
    _keccak = None

if TYPE_CHECKING:
    from requests import Session

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

# … (rest of your Explorer classes unchanged) …

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
        {"network": network, **match.to_dict()}
        for network, network_matches in sorted(matches_by_network.items())
        for match in network_matches
    ]
    report["match_count"] = len(report["matching_contracts"])
    return report
