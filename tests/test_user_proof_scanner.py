from typing import Iterator, List

from scan_user_proof_hub import (
    BlockscoutExplorer,
    ContractMatch,
    ExplorerContract,
    EVENT_TOPICS,
    FUNCTION_SELECTORS,
    KEYWORDS,
    build_proof_report,
    collect_unique_addresses,
    compute_event_topics,
    compute_function_selectors,
    find_matches,
    scan_network,
)


def test_compute_function_selectors_matches_known_values():
    abi = [
        {
            "type": "function",
            "name": "verify",
            "inputs": [
                {"name": "user", "type": "address"},
                {"name": "proof", "type": "bytes32"},
            ],
        },
        {
            "type": "function",
            "name": "transportProof",
            "inputs": [
                {"name": "user", "type": "address"},
                {"name": "proof", "type": "bytes32"},
                {"name": "uri", "type": "string"},
            ],
        },
    ]

    selectors = compute_function_selectors(abi)

    assert "verify(address,bytes32)" in selectors
    assert selectors["verify(address,bytes32)"] == FUNCTION_SELECTORS["verify(address,bytes32)"]
    assert "transportProof(address,bytes32,string)" in selectors
    assert (
        selectors["transportProof(address,bytes32,string)"]
        == FUNCTION_SELECTORS["transportProof(address,bytes32,string)"]
    )


def test_compute_event_topics_matches_known_values():
    abi = [
        {
            "type": "event",
            "name": "ProofVerified",
            "inputs": [
                {"name": "user", "type": "address", "indexed": True},
                {"name": "proof", "type": "bytes32", "indexed": False},
            ],
        }
    ]

    topics = compute_event_topics(abi)

    assert "ProofVerified(address,bytes32)" in topics
    assert (
        topics["ProofVerified(address,bytes32)"]
        == EVENT_TOPICS["ProofVerified(address,bytes32)"]
    )


def test_find_matches_reports_all_indicators():
    abi = [
        {
            "type": "function",
            "name": "verify",
            "inputs": [
                {"name": "user", "type": "address"},
                {"name": "proof", "type": "bytes32"},
            ],
        },
        {
            "type": "event",
            "name": "ProofVerified",
            "inputs": [
                {"name": "user", "type": "address", "indexed": True},
                {"name": "proof", "type": "bytes32", "indexed": False},
            ],
        },
    ]
    source = "\n".join(KEYWORDS)
    contract = ExplorerContract(
        address="0x123",
        name="UserProofHub",
        explorer_url="https://example",
        abi=abi,
        source_text=source,
    )

    match = find_matches(contract)
    assert match is not None
    assert any("Function selectors" in reason for reason in match.reasons)
    assert any("Events present" in reason for reason in match.reasons)
    assert any("Keywords present" in reason for reason in match.reasons)


class DummyExplorer(BlockscoutExplorer):
    def __init__(self, search_results: List[dict], contracts: List[ExplorerContract]):
        self.search_results = search_results
        self.contracts = {c.address.lower(): c for c in contracts}

    def iter_text_search(self, query: str, *, page_size: int = 50, max_pages=None) -> Iterator[dict]:
        yield from self.search_results

    def fetch_contract(self, address: str) -> ExplorerContract:
        return self.contracts[address]


def test_scan_network_deduplicates_addresses():
    contract = ExplorerContract(
        address="0xabc",
        name="UserProofHub",
        explorer_url="https://example",
        abi=[
            {
                "type": "function",
                "name": "verify",
                "inputs": [
                    {"name": "user", "type": "address"},
                    {"name": "proof", "type": "bytes32"},
                ],
            }
        ],
        source_text="",
    )
    search_results = [
        {"address_hash": "0xAbC"},
        {"address": "0xabc"},
    ]
    explorer = DummyExplorer(search_results, [contract])

    matches = scan_network(
        explorer,
        page_size=10,
        max_pages=1,
        indicators=[FUNCTION_SELECTORS["verify(address,bytes32)"]],
    )

    assert len(matches) == 1
    assert isinstance(matches[0], ContractMatch)
    assert matches[0].contract.address == "0xabc"


def test_collect_unique_addresses():
    match_a = ContractMatch(
        contract=ExplorerContract(address="0xAbC", name=None, explorer_url="https://one"),
        reasons=["selectors"],
    )
    match_b = ContractMatch(
        contract=ExplorerContract(address="0xdef", name=None, explorer_url="https://two"),
        reasons=["events"],
    )

    addresses = collect_unique_addresses({"avalanche": [match_a], "base": [match_b, match_a]})

    assert addresses == ["0xabc", "0xdef"]


def test_build_proof_report_includes_contracts():
    match = ContractMatch(
        contract=ExplorerContract(address="0xabc", name="UserProofHub", explorer_url="https://one"),
        reasons=["selectors"],
    )
    template = {"source": "SoulSync / KinKey Protocol"}

    report = build_proof_report(template, {"avalanche": [match]})

    assert template == {"source": "SoulSync / KinKey Protocol"}
    assert report["matching_addresses"] == ["0xabc"]
    assert report["match_count"] == 1
    assert report["matching_contracts"] == [
        {
            "network": "avalanche",
            "address": "0xabc",
            "name": "UserProofHub",
            "explorer_url": "https://one",
            "reasons": ["selectors"],
        }
    ]
