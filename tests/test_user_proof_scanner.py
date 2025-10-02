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
