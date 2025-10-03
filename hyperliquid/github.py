"""Utilities for interacting with the GitHub commits API.

Resilient extraction of commit authorship metadata, handling cases where
`author` is null (unlinked emails), and exposing fallbacks from commit/committer
fields. Provides both detailed and backward-compatible simplified views.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Any

try:  # pragma: no cover - exercised indirectly in tests
    import requests
except ImportError:  # fallback for restricted environments
    class _RequestsStub:
        class HTTPError(RuntimeError): ...
        class Session:  # type: ignore[override]
            def get(self, *_args, **_kwargs):
                raise RuntimeError("The 'requests' dependency is required to perform HTTP calls")
    requests = _RequestsStub()  # type: ignore[assignment]

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommitAuthor:
    """Rich container for author metadata."""
    login: Optional[str]
    name: Optional[str]
    email: Optional[str]
    source: Optional[str]

    @property
    def identifier(self) -> Optional[str]:
        """Return a preferred identifier string (login > name > email)."""
        for v in (self.login, self.name, self.email):
            if isinstance(v, str) and v:
                return v
        return None


def _as_str(mapping: Mapping[str, Any], key: str) -> Optional[str]:
    v = mapping.get(key)
    return v if isinstance(v, str) and v else None


def _extract_commit_author_details(commit: Mapping[str, Any]) -> Optional[CommitAuthor]:
    """Extract rich author details from a GitHub commit payload."""
    if not isinstance(commit, Mapping):
        return None

    # unwrap GraphQL node if present
    node = commit.get("node")
    if isinstance(node, Mapping):
        commit = node

    # Try `author`
    author_obj = commit.get("author")
    if isinstance(author_obj, Mapping):
        login = _as_str(author_obj, "login")
        source = "author"
        if login is None:
            user_obj = author_obj.get("user")
            if isinstance(user_obj, Mapping):
                login = _as_str(user_obj, "login")
                if login:
                    source = "author.user"
        name = _as_str(author_obj, "name")
        email = _as_str(author_obj, "email")
        if any((login, name, email)):
            return CommitAuthor(login=login, name=name, email=email, source=source)

    # Try `commit.author`
    commit_obj = commit.get("commit")
    if isinstance(commit_obj, Mapping):
        ca = commit_obj.get("author")
        if isinstance(ca, Mapping):
            name = _as_str(ca, "name")
            email = _as_str(ca, "email")
            if any((name, email)):
                return CommitAuthor(login=None, name=name, email=email, source="commit.author")

    # Try `committer`
    committer_obj = commit.get("committer")
    if isinstance(committer_obj, Mapping):
        login = _as_str(committer_obj, "login")
        name = _as_str(committer_obj, "name")
        email = _as_str(committer_obj, "email")
        if any((login, name, email)):
            return CommitAuthor(login=login, name=name, email=email, source="committer")

    # Try `commit.committer`
    if isinstance(commit_obj, Mapping):
        cc = commit_obj.get("committer")
        if isinstance(cc, Mapping):
            name = _as_str(cc, "name")
            email = _as_str(cc, "email")
            if any((name, email)):
                return CommitAuthor(login=None, name=name, email=email, source="commit.committer")

    return None


class GitHubAPIError(RuntimeError):
    """Raised when the GitHub API responds with an unexpected payload."""


def _normalise_repo(repo: str) -> str:
    """Return `owner/name` for GitHub repository strings."""
    if repo.startswith("https://github.com/"):
        repo = repo[len("https://github.com/") :]
    return repo.strip("/")


@dataclass
class GitHubSourceControlHistoryItemDetailsProvider:
    """Wrapper around the GitHub commits API with attribution helpers."""

    token: Optional[str] = None
    session: Optional[requests.Session] = None
    timeout: Optional[float] = 10.0

    _API_ROOT = "https://api.github.com"

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()
        self._headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "claim-kin-agent-attribution/1.0",
        }
        if self.token:
            self._headers["Authorization"] = f"Bearer {self.token}"

    def _get_commit(self, repo: str, sha: str) -> Dict[str, Any]:
        repo_path = _normalise_repo(repo)
        url = f"{self._API_ROOT}/repos/{repo_path}/commits/{sha}"
        response = self.session.get(url, headers=self._headers, timeout=self.timeout)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:  # type: ignore[attr-defined]
            raise GitHubAPIError(f"GitHub API error for {repo_path}@{sha}: {exc}") from exc
        data = response.json()
        if not isinstance(data, Mapping):
            raise GitHubAPIError(f"Unexpected payload for {repo_path}@{sha}: {data!r}")
        return dict(data)

    def get_commit_author_details(self, repo: str, sha: str) -> Optional[CommitAuthor]:
        """Return rich author object."""
        commit = self._get_commit(repo, sha)
        details = _extract_commit_author_details(commit)
        if details is None:
            _LOGGER.warning("Commit %s/%s has no author", _normalise_repo(repo), sha)
        return details

    def get_commit_author(self, repo: str, sha: str) -> Optional[str]:
        """Return the preferred string identifier for a commit (login > name > email)."""
        details = self.get_commit_author_details(repo, sha)
        return details.identifier if details else None

    def get_commit_authors(self, repo: str, shas: Iterable[str]) -> Dict[str, Optional[CommitAuthor]]:
        """Fetch authors for a set of commits."""
        results: Dict[str, Optional[CommitAuthor]] = {}
        repo_path = _normalise_repo(repo)
        for sha in shas:
            try:
                results[sha] = self.get_commit_author_details(repo_path, sha)
            except GitHubAPIError as exc:
                _LOGGER.warning("Failed to fetch commit %s/%s: %s", repo_path, sha, exc)
                results[sha] = None
        return results
