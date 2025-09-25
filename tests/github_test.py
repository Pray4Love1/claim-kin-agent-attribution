import logging
from typing import Dict

from hyperliquid import github as github_module
from hyperliquid.github import (
    CommitAuthor,
    GitHubSourceControlHistoryItemDetailsProvider,
)


class FakeResponse:
    def __init__(self, json_data: Dict[str, object]):
        self._json = json_data

    def json(self) -> Dict[str, object]:
        return self._json


class FakeSession:
    def __init__(self, responses: Dict[str, FakeResponse]):
        self._responses = responses

    def get(self, url, headers=None, timeout=None):
        return self._responses.get(url)


def test_extract_commit_author_details_uses_committer_information():
    provider = GitHubSourceControlHistoryItemDetailsProvider(
        session=FakeSession(
            {
                "deadbeef": FakeResponse(
                    {
                        "commit": {
                            "author": {"name": "Alice", "email": "alice@example.com"},
                            "committer": {
                                "name": "Bob",
                                "email": "bob@example.com",
                            },
                        }
                    }
                )
            }
        )
    )
    details = provider.get_commit_author_details("foo/bar", "deadbeef")
    assert isinstance(details, CommitAuthor)
    assert details.name == "Bob"
    assert details.email == "bob@example.com"


def test_get_commit_author_details_logs_when_missing(caplog):
    caplog.set_level(logging.WARNING)
    provider = GitHubSourceControlHistoryItemDetailsProvider(
        session=FakeSession(
            {
                "deadbeef": FakeResponse({"commit": {"author": {}}}),
            }
        )
    )
    details = provider.get_commit_author_details("foo/bar", "deadbeef")
    assert details is None
