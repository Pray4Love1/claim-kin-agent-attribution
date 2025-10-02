import logging
from typing import Dict

from hyperliquid import github as github_module
from hyperliquid.github import (
    CommitAuthor,
    GitHubSourceControlHistoryItemDetailsProvider,
    _extract_commit_author_details,
    _normalise_repo,
)


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise github_module.requests.HTTPError(f"{self.status_code} error")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses: Dict[str, FakeResponse]):
        self._responses = responses

    def get(self, url, headers=None, timeout=None):
        sha = url.rsplit("/", 1)[-1]
        response = self._responses.get(sha)
        if response is None:
            raise AssertionError(f"Unexpected URL: {url}")
        return response


def test_normalise_repo_handles_full_urls():
    assert _normalise_repo("https://github.com/foo/bar/") == "foo/bar"
    assert _normalise_repo("foo/bar") == "foo/bar"


def test_extract_commit_author_details_prefers_login():
    commit = {
        "author": {"login": "octocat", "name": "Octo Cat", "email": "octo@cat"},
        "commit": {"author": {"name": "Fallback", "email": "fallback@example.com"}},
    }
    details = _extract_commit_author_details(commit)
    assert isinstance(details, CommitAuthor)
    assert details.identifier == "octocat"
    assert details.source == "author"


def test_extract_commit_author_details_falls_back_to_commit_data():
    commit = {
        "author": None,
        "commit": {"author": {"name": "Anon", "email": "anon@example.com"}},
    }
    details = _extract_commit_author_details(commit)
    assert isinstance(details, CommitAuthor)
    assert details.identifier == "Anon"
    assert details.source == "commit.author"


def test_extract_commit_author_details_uses_committer_information():
    commit = {
        "author": None,
        "commit": {"author": None, "committer": {"name": "Merge Bot"}},
        "committer": {"login": "merge-bot"},
    }
    details = _extract_commit_author_details(commit)
    assert isinstance(details, CommitAuthor)
    assert details.identifier == "merge-bot"
    assert details.source == "committer"


def test_get_commit_author_details_logs_when_missing(caplog):
    caplog.set_level(logging.WARNING)
    provider = GitHubSourceControlHistoryItemDetailsProvider(
        session=FakeSession({
            "deadbeef": FakeResponse({"commit": {"author": {}}}),
        })
    )
    details = provider.get_commit_author_details("foo/bar", "deadbeef")
    assert details is None
    assert "does not expose an author" in caplog.text


def test_get_commit_authors_handles_errors(caplog):
    caplog.set_level(logging.WARNING)
    provider = GitHubSourceControlHistoryItemDetailsProvider(
        session=FakeSession(
            {
                "good": FakeResponse({"author": {"login": "octocat"}}),
                "bad": FakeResponse({}, status_code=500),
            }
        )
    )
    results = provider.get_commit_authors("foo/bar", ["good", "bad"])
    assert isinstance(results["good"], CommitAuthor)
    assert results["good"].identifier == "octocat"
    assert results["bad"] is None
    assert "Failed to fetch GitHub commit" in caplog.text


def test_get_commit_author_compatibility_wrapper_returns_identifier():
    provider = GitHubSourceControlHistoryItemDetailsProvider(
        session=FakeSession({"good": FakeResponse({"author": {"name": "Tester"}})})
    )
    assert provider.get_commit_author("foo/bar", "good") == "Tester"


def test_get_commit_authors_uses_normalised_repo():
    provider = GitHubSourceControlHistoryItemDetailsProvider(
        session=FakeSession({"sha": FakeResponse({"author": {"login": "octocat"}})})
    )
    results = provider.get_commit_authors("https://github.com/foo/bar", ["sha"])
    assert results["sha"].identifier == "octocat"
