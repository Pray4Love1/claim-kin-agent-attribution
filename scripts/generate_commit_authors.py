"""Generate a commit SHA to author mapping for attribution records."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:  # pragma: no cover - optional dependency for offline environments
    import requests
except ModuleNotFoundError:  # pragma: no cover - fallback when requests is unavailable
    import json as _json
    import sys as _sys
    from types import ModuleType
    from urllib import request as _urllib_request

    class _FallbackResponse:
        def __init__(self, status_code: int, data: bytes):
            self.status_code = status_code
            self._data = data

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP error status: {self.status_code}")

        def json(self):  # type: ignore[override]
            return _json.loads(self._data.decode("utf-8"))

    class _FallbackSession:
        def __init__(self) -> None:
            self.headers: Dict[str, str] = {}

        def get(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 10):
            request_headers = dict(self.headers)
            if headers:
                request_headers.update(headers)
            req = _urllib_request.Request(url, headers=request_headers)
            with _urllib_request.urlopen(req, timeout=timeout) as resp:  # type: ignore[arg-type]
                data = resp.read()
                return _FallbackResponse(status_code=resp.status, data=data)

    _requests_module = ModuleType("requests")
    _requests_module.Session = _FallbackSession  # type: ignore[attr-defined]
    _sys.modules.setdefault("requests", _requests_module)
    requests = _requests_module

from claim_kin_agent_attribution.github_helpers import (
    CommitAuthor,
    GitHubSourceControlHistoryItemDetailsProvider,
)

DEFAULT_OUTPUT = Path("data/commit_author_map.json")


def _parse_repo_slug(remote: str) -> Optional[str]:
    remote = remote.strip()
    if not remote:
        return None
    if remote.endswith(".git"):
        remote = remote[:-4]
    if remote.startswith("git@github.com:"):
        return remote.split(":", 1)[1]
    if remote.startswith("https://github.com/"):
        return remote.split("github.com/", 1)[1]
    if remote.startswith("http://github.com/"):
        return remote.split("github.com/", 1)[1]
    if "/" in remote:
        # Already looks like owner/repo
        return remote
    return None


def _detect_repo_slug() -> Optional[str]:
    env_repo = os.getenv("GITHUB_REPOSITORY")
    if env_repo:
        parsed = _parse_repo_slug(env_repo)
        if parsed:
            return parsed
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return None
    return _parse_repo_slug(result.stdout.strip())


def _recent_commits(limit: int, rev: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "rev-list", f"--max-count={limit}", rev],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - subprocess failure
        raise SystemExit(f"Unable to list commits: {exc}") from exc
    commits = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not commits:
        raise SystemExit("No commits found for the provided revision range.")
    return commits


def _local_authors(commits: Iterable[str]) -> Dict[str, Optional[CommitAuthor]]:
    authors: Dict[str, Optional[CommitAuthor]] = {}
    for sha in commits:
        try:
            result = subprocess.run(
                ["git", "show", "-s", "--format=%an", sha],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            authors[sha] = None
            continue
        name = result.stdout.strip()
        if name:
            authors[sha] = CommitAuthor(identifier=name, source="git.log")
        else:
            authors[sha] = None
    return authors


def _build_session(token: Optional[str]) -> requests.Session:
    session = requests.Session()
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    session.headers.setdefault("User-Agent", "claim-kin-attribution/1.0")
    return session


def _prepare_output_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _serialise_author(author: Optional[CommitAuthor]) -> Optional[Dict[str, str]]:
    if author is None:
        return None
    return {"identifier": author.identifier, "source": author.source}


def generate_author_map(repo: str, commits: Iterable[str], token: Optional[str]) -> Dict[str, Optional[CommitAuthor]]:
    session = _build_session(token)
    provider = GitHubSourceControlHistoryItemDetailsProvider(session=session)
    author_map = provider.get_commit_authors(repo, commits)

    # Fallback for commits where GitHub does not provide an author (or the request failed).
    missing = [sha for sha, author in author_map.items() if author is None]
    if missing:
        local = _local_authors(missing)
        for sha in missing:
            if author_map[sha] is None and local.get(sha) is not None:
                author_map[sha] = local[sha]
    return author_map


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a commit-to-author mapping for attribution ledgers.")
    parser.add_argument(
        "--repo",
        default=_detect_repo_slug(),
        help="Repository slug in the form owner/name. Defaults to the origin remote.",
    )
    parser.add_argument(
        "--rev",
        default="HEAD",
        help="Revision or ref to start from. Passed to git rev-list (default: HEAD).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Number of commits to include in the mapping (default: 50).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path where the commit author map should be written (default: data/commit_author_map.json).",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub token used for authenticated requests (defaults to GITHUB_TOKEN env var).",
    )
    args = parser.parse_args(argv)

    if not args.repo:
        raise SystemExit("Unable to determine the repository slug. Provide --repo explicitly.")

    commits = _recent_commits(args.limit, args.rev)
    author_map = generate_author_map(args.repo, commits, args.token)

    payload = {
        "repo": args.repo,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commits": {sha: _serialise_author(author) for sha, author in author_map.items()},
    }

    _prepare_output_directory(args.output)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Wrote author map for {len(commits)} commits to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
