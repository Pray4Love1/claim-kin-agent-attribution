import textwrap

import pytest

from hyperliquid.deployments import format_summary, load_transactions


def test_load_transactions_parses_multiple_blocks(tmp_path):
    sample = textwrap.dedent(
        """
        {
          "bundle": "0xabc",
          "transactions": [
            {
              "hash": "0x1",
              "contractAddress": "0x123",
              "transaction": {
                "chainId": "0x64",
                "from": "0xfeed"
              }
            },
            {
              "hash": "0x2",
              "transaction": {
                "chainId": 42,
                "from": "0xbeef"
              }
            }
          ]
        }

        trailing metadata

        "transactions": [
          {
            "hash": "0x3",
            "contractAddress": "0x999",
            "transaction": {
              "chainId": "0x1",
              "from": "0xaaaa"
            }
          }
        ]
        """
    )
    path = tmp_path / "deplo.txt"
    path.write_text(sample, encoding="utf-8")

    transactions = load_transactions(path)

    assert [tx["hash"] for tx in transactions] == ["0x1", "0x2", "0x3"]
    assert transactions[0]["contractAddress"] == "0x123"
    assert transactions[1]["contractAddress"] is None
    assert transactions[1]["chainId"] == "42"
    assert transactions[2]["from"] == "0xaaaa"


def test_load_transactions_requires_transactions_block(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("no transactions here", encoding="utf-8")

    with pytest.raises(ValueError):
        load_transactions(path)


def test_format_summary_matches_expected_output():
    transactions = [
        {
            "contractAddress": "0xAAA",
            "hash": "0x111",
            "chainId": "0x1",
            "from": "0xabc",
        }
    ]

    summary = format_summary(transactions)

    expected = (
        "\n🧠 Parsed 1 contract deployments:\n\n"
        "📦 Contract:  0xAAA\n"
        "🔗 Tx Hash:   0x111\n"
        "🌐 Chain ID:  0x1\n"
        "🚀 From:      0xabc\n"
        "------------------------------------------------------------"
    )

    assert summary == expected
