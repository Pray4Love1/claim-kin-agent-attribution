"""Minimal GitHub helper utilities used by the test-suite."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional

from . import api  # re-exported for tests expecting requests attribute

requests = api.requests  # type: ignore[attr-defined]

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommitAuthor:
    """Simple container describing the author attached to a Git commit."""

    identifier: str
    source: str


def _normalise_repo(repo: str) -> str:
    """Return the ``owner/name`` fragment for a GitHub repository string."""
    prefix = "https://github.com/"
    if repo.startswith(prefix):
        repo = repo[len(prefix) :]
    return repo.strip("/")


def _extract_commit_author_details(commit_payload: Mapping[str, object]) -> Optional[CommitAuthor]:
    """Extract author information from the GitHub commit payload."""
    author = commit_payload.get("author") if isinstance(commit_payload, Mapping) else None
    if isinstance(author, Mapping):
        login = author.get("login")
        if isinstance(login, str) and login:
            return CommitAuthor(identifier=login, source="author")
        name = author.get("name")
        if isinstance(name, str) and name:
            return CommitAuthor(identifier=name, source="author")
    committer = commit_payload.get("committer") if isinstance(commit_payload, Mapping) else None
    if isinstance(committer, Mapping):
        login = committer.get("login")
        if isinstance(login, str) and login:
            return CommitAuthor(identifier=login, source="committer")
    commit_meta = commit_payload.get("commit") if isinstance(commit_payload, Mapping) else None
    if isinstance(commit_meta, Mapping):
        commit_author = commit_meta.get("author")
        if isinstance(commit_author, Mapping):
            name = commit_author.get("name")
            if isinstance(name, str) and name:
                return CommitAuthor(identifier=name, source="commit.author")
        commit_committer = commit_meta.get("committer")
        if isinstance(commit_committer, Mapping):
            name = commit_committer.get("name")
            if isinstance(name, str) and name:
                return CommitAuthor(identifier=name, source="commit.committer")
    return None


class GitHubSourceControlHistoryItemDetailsProvider:
    """Fetch commit metadata from GitHub for attribution analytics."""

    _API_URL = "https://api.github.com/repos/{repo}/commits/{sha}"

    def __init__(self, session: Optional[requests.Session] = None) -> None:  # type: ignore[name-defined]
        self._session = session or requests.Session()  # type: ignore[attr-defined]

    def get_commit_author_details(self, repo: str, sha: str) -> Optional[CommitAuthor]:
        """Return commit author metadata or ``None`` when unavailable."""
        normalised_repo = _normalise_repo(repo)
        url = self._API_URL.format(repo=normalised_repo, sha=sha)
        try:
            response = self._session.get(url, headers={"Accept": "application/vnd.github+json"}, timeout=10)
            response.raise_for_status()
        except Exception:  # pragma: no cover - network errors are logged and reported as None
            _LOGGER.warning("Failed to fetch GitHub commit %s:%s", normalised_repo, sha)
            return None
        payload = response.json()
        details = _extract_commit_author_details(payload)
        if details is None:
            _LOGGER.warning("Commit %s:%s does not expose an author", normalised_repo, sha)
        return details

    def get_commit_authors(self, repo: str, shas: Iterable[str]) -> Dict[str, Optional[CommitAuthor]]:
        """Batch lookup helper used by attribution pipelines."""
        results: Dict[str, Optional[CommitAuthor]] = {}
        for sha in shas:
            details = self.get_commit_author_details(repo, sha)
            if details is None:
                _LOGGER.warning("Failed to fetch GitHub commit %s:%s", _normalise_repo(repo), sha)
            results[sha] = details
        return results

    def get_commit_author(self, repo: str, sha: str) -> Optional[str]:
        """Backward-compatible wrapper returning only the identifier string."""
        details = self.get_commit_author_details(repo, sha)
        return details.identifier if details else None
