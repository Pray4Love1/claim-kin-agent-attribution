"""Utilities for fetching commit author information from GitHub."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

try:  # pragma: no cover - exercised indirectly in tests
    import requests
except ImportError:  # pragma: no cover - lightweight fallback for restricted environments
    class _RequestException(Exception):
        """Replacement for :class:`requests.RequestException` when requests isn't available."""

    class _HTTPError(_RequestException):
        """Replacement for :class:`requests.HTTPError` when requests isn't available."""

    class _Session:  # minimal shim used only for typing
        def get(self, *args, **kwargs):  # noqa: D401 - intentionally minimal
            raise NotImplementedError("HTTP requests require the requests package")

    class _RequestsModule:
        HTTPError = _HTTPError
        RequestException = _RequestException
        Session = _Session

    requests = _RequestsModule()  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommitAuthor:
    """Represents an author returned from the GitHub commits API."""

    identifier: str
    source: str


def _extract_identifier(candidate: Optional[dict], source: str) -> Optional[CommitAuthor]:
    """Extract a usable identifier from a GitHub API payload."""

    if not candidate:
        return None
    login = candidate.get("login")
    if isinstance(login, str) and login:
        return CommitAuthor(identifier=login, source=source)
    name = candidate.get("name")
    if isinstance(name, str) and name:
        return CommitAuthor(identifier=name, source=source)
    email = candidate.get("email")
    if isinstance(email, str) and email:
        return CommitAuthor(identifier=email, source=source)
    return None


def _extract_commit_author_details(commit_payload: dict) -> Optional[CommitAuthor]:
    """Derive commit author information from a GitHub commit payload."""

    # Prefer the author field when available as it contains the GitHub login.
    details = _extract_identifier(commit_payload.get("author"), "author")
    if details is not None:
        return details

    commit_section = commit_payload.get("commit") or {}
    details = _extract_identifier(commit_section.get("author"), "commit.author")
    if details is not None:
        return details

    details = _extract_identifier(commit_payload.get("committer"), "committer")
    if details is not None:
        return details

    details = _extract_identifier(commit_section.get("committer"), "commit.committer")
    if details is not None:
        return details

    return None


def _normalise_repo(repo: str) -> str:
    """Normalise a GitHub repository identifier into the form ``owner/name``."""

    repo = repo.strip()
    if repo.endswith("/"):
        repo = repo[:-1]

    prefixes = (
        "https://github.com/",
        "http://github.com/",
        "git@github.com:",
        "github.com/",
    )
    for prefix in prefixes:
        if repo.startswith(prefix):
            repo = repo[len(prefix) :]
            break
    if repo.endswith(".git"):
        repo = repo[: -len(".git")]
    return repo


class GitHubSourceControlHistoryItemDetailsProvider:
    """Fetch commit author details using the GitHub REST API."""

    _API_URL_TEMPLATE = "https://api.github.com/repos/{repo}/commits/{sha}"

    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()

    def get_commit_author_details(self, repo: str, sha: str) -> Optional[CommitAuthor]:
        """Return author details for the given commit, or ``None`` if unavailable."""

        normalised_repo = _normalise_repo(repo)
        url = self._API_URL_TEMPLATE.format(repo=normalised_repo, sha=sha)
        try:
            response = self._session.get(url, headers={"Accept": "application/vnd.github+json"}, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:  # type: ignore[attr-defined]
            LOGGER.warning("Failed to fetch GitHub commit %s@%s: %s", normalised_repo, sha, exc)
            return None

        payload = response.json()
        details = _extract_commit_author_details(payload)
        if details is None:
            LOGGER.warning("Commit %s@%s does not expose an author", normalised_repo, sha)
        return details

    def get_commit_authors(self, repo: str, shas: Iterable[str]) -> Dict[str, Optional[CommitAuthor]]:
        """Fetch author information for multiple commits in the provided repository."""

        results: Dict[str, Optional[CommitAuthor]] = {}
        for sha in shas:
            results[sha] = self.get_commit_author_details(repo, sha)
        return results

    def get_commit_author(self, repo: str, sha: str) -> Optional[str]:
        """Compatibility helper returning only the author identifier."""

        details = self.get_commit_author_details(repo, sha)
        return None if details is None else details.identifier
