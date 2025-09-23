"""Utilities for interacting with the GitHub commits API.

This module contains a lightweight re-implementation of the logic that was
previously embedded in the TypeScript `GitHubSourceControlHistoryItemDetailsProvider`.
The original implementation expected the REST response to *always* contain an
`author` object.  However, GitHub returns ``null`` for the ``author`` field when
the commit email is not attached to a GitHub account.  Attempting to read the
``login`` or ``name`` attributes in that scenario raised a ``TypeError``.

To make the attribution tooling resilient we provide helpers that extract rich
author information while gracefully handling ``null`` values.  The helpers fall
back to metadata embedded inside ``commit.author`` or the committer fields when
the top-level GitHub user objects are missing.  This mirrors the behaviour of
the GitHub UI, ensures that commits authored with unlinked emails are still
attributable, and gives callers enough detail to "fetch the thieves" behind
mysterious commits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional

try:  # pragma: no cover - exercised implicitly when the dependency is available
    import requests
except ModuleNotFoundError:  # pragma: no cover - provides a lightweight fallback for tests
    class _RequestsStub:
        class HTTPError(RuntimeError):
            """Placeholder that mimics the real ``requests.HTTPError`` API."""

            pass

        class Session:  # type: ignore[override]
            def get(self, *_args, **_kwargs):
                raise RuntimeError("The 'requests' dependency is required to perform HTTP calls")

    requests = _RequestsStub()  # type: ignore[assignment]


_LOGGER = logging.getLogger(__name__)


class GitHubAPIError(RuntimeError):
    """Raised when the GitHub API responds with an unexpected payload."""


def _normalise_repo(repo: str) -> str:
    """Normalise ``owner/repo`` inputs by stripping protocol prefixes.

    The attribution tooling sometimes receives repository identifiers in
    ``https://github.com/<owner>/<repo>`` form.  For the REST API we only need
    the ``owner/repo`` portion, so this helper keeps the public surface lenient
    while avoiding repeated string parsing at callsites.
    """

    if repo.startswith("https://github.com/"):
        repo = repo[len("https://github.com/") :]
    return repo.strip("/")


@dataclass(frozen=True)
class CommitAuthor:
    """Container for the different pieces of author metadata GitHub exposes."""

    login: Optional[str]
    name: Optional[str]
    email: Optional[str]
    source: Optional[str]

    @property
    def identifier(self) -> Optional[str]:
        """Return the most helpful human readable identifier available."""

        for value in (self.login, self.name, self.email):
            if isinstance(value, str) and value:
                return value
        return None


def _as_str(mapping: Mapping[str, Any], key: str) -> Optional[str]:
    value = mapping.get(key)
    return value if isinstance(value, str) and value else None


def _extract_commit_author_details(commit: Mapping[str, Any]) -> Optional[CommitAuthor]:
    """Extract detailed author information from a GitHub commit payload.

    The payload contains up to four locations that may reference the author:

    ``author``
        GitHub user object, present only when the email maps to an account.

    ``commit.author``
        Raw author data embedded inside the commit.

    ``committer``
        GitHub user responsible for applying the commit, useful for merges.

    ``commit.committer``
        Raw committer information embedded inside the commit.

    Returning the dataclass instead of a bare string gives callers access to the
    full set of metadata so they can decide how to attribute the change.  The
    :pyattr:`CommitAuthor.identifier` property mirrors the behaviour of the old
    helper by picking the most helpful identifier.
    """

    if not isinstance(commit, Mapping):
        return None

    # GitHub's GraphQL API often wraps commit nodes inside a ``{"node": ...}``
    # container.  Unwrap that structure to keep the extraction logic focused on
    # the raw commit payload regardless of where it originated from.
    node = commit.get("node")
    if isinstance(node, Mapping):
        commit = node

    author_obj = commit.get("author")
    if isinstance(author_obj, Mapping):
        login = _as_str(author_obj, "login")
        source = "author"

        # GraphQL responses may expose the GitHub user object under
        # ``author.user`` instead of directly on ``author``.  When present we
        # surface the nested login as the preferred identifier.
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

    commit_obj = commit.get("commit")
    if isinstance(commit_obj, Mapping):
        commit_author = commit_obj.get("author")
        if isinstance(commit_author, Mapping):
            name = _as_str(commit_author, "name")
            email = _as_str(commit_author, "email")
            if any((name, email)):
                return CommitAuthor(login=None, name=name, email=email, source="commit.author")

    committer_obj = commit.get("committer")
    if isinstance(committer_obj, Mapping):
        login = _as_str(committer_obj, "login")
        name = _as_str(committer_obj, "name")
        email = _as_str(committer_obj, "email")
        if any((login, name, email)):
            return CommitAuthor(login=login, name=name, email=email, source="committer")

    if isinstance(commit_obj, Mapping):
        commit_committer = commit_obj.get("committer")
        if isinstance(commit_committer, Mapping):
            name = _as_str(commit_committer, "name")
            email = _as_str(commit_committer, "email")
            if any((name, email)):
                return CommitAuthor(login=None, name=name, email=email, source="commit.committer")

    return None


@dataclass
class GitHubSourceControlHistoryItemDetailsProvider:
    """Simple wrapper around the GitHub commits API.

    Parameters
    ----------
    token:
        Optional personal access token used for authenticated requests.  Passing
        a token increases rate limits but is not required.
    session:
        Optional :class:`requests.Session` instance to reuse connections during
        batch queries (useful in tests).
    timeout:
        Per-request timeout in seconds.
    """

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

    # Public API ---------------------------------------------------------
    def get_commit_author_details(self, repo: str, commit_sha: str) -> Optional[CommitAuthor]:
        """Fetch the richest author metadata available for ``commit_sha``."""

        commit = self._get_commit(repo, commit_sha)
        details = _extract_commit_author_details(commit)
        if details is None:
            _LOGGER.warning(
                "GitHub commit %s/%s does not expose an author", _normalise_repo(repo), commit_sha
            )
        return details

    def get_commit_author(self, repo: str, commit_sha: str) -> Optional[str]:
        """Compatibility wrapper returning just the preferred identifier."""

        details = self.get_commit_author_details(repo, commit_sha)
        return None if details is None else details.identifier

    def get_commit_authors(
        self, repo: str, commit_shas: Iterable[str]
    ) -> Dict[str, Optional[CommitAuthor]]:
        """Batch variant of :meth:`get_commit_author_details`.

        Any GitHub API errors are logged and represented with ``None`` entries in
        the resulting dictionary so that callers can continue processing the
        remaining commits.  This mirrors the "best effort" goal of the original
        TypeScript helper while providing enough data to "fetch the thieves" that
        authored each change.
        """

        results: Dict[str, Optional[CommitAuthor]] = {}
        repo_path = _normalise_repo(repo)
        for sha in commit_shas:
            try:
                results[sha] = self.get_commit_author_details(repo_path, sha)
            except GitHubAPIError as exc:
                _LOGGER.warning("Failed to fetch GitHub commit %s/%s: %s", repo_path, sha, exc)
                results[sha] = None
        return results

    # Internal helpers ---------------------------------------------------
    def _get_commit(self, repo: str, commit_sha: str) -> Dict[str, Any]:
        repo_path = _normalise_repo(repo)
        url = f"{self._API_ROOT}/repos/{repo_path}/commits/{commit_sha}"
        response = self.session.get(url, headers=self._headers, timeout=self.timeout)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - exercised in integration tests
            raise GitHubAPIError(f"GitHub API error for {repo_path}@{commit_sha}: {exc}") from exc

        data = response.json()
        if not isinstance(data, Mapping):
            raise GitHubAPIError(f"Unexpected payload when fetching commit {repo_path}@{commit_sha}: {data!r}")
        return dict(data)

