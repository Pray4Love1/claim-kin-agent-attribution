"""Test configuration to avoid external dependencies during CI and provide plugin stubs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import sys
from types import ModuleType

import pytest

# ---------------------------------------------------------------------------
# Compatibility shims for missing optional dependencies
# ---------------------------------------------------------------------------

try:  # pragma: no cover - exercised only in environments with requests
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for the execution environment
    class _DummySession:
        """Minimal drop-in replacement for requests.Session."""

        def __init__(self) -> None:
            self.headers: Dict[str, str] = {}

        def post(self, url: str, json: Dict[str, Any] | None = None, timeout: float | None = None):
            raise RuntimeError("Network access is disabled in the test environment")

    requests = ModuleType("requests")
    requests.Session = _DummySession  # type: ignore[attr-defined]
    requests.HTTPError = RuntimeError  # type: ignore[attr-defined]
    sys.modules["requests"] = requests

try:  # pragma: no cover - executed only when websocket-client is missing
    import websocket  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for tests
    class _DummyWebSocketApp:
        def __init__(self, *_args, **_kwargs) -> None:
            self.keep_running = False

        def run_forever(self) -> None:  # pragma: no cover
            return None

        def send(self, _message: str) -> None:
            return None

        def close(self) -> None:
            return None

    websocket = ModuleType("websocket")
    websocket.WebSocketApp = _DummyWebSocketApp  # type: ignore[attr-defined]
    sys.modules["websocket"] = websocket

# ---------------------------------------------------------------------------
# Hyperliquid API stub
# ---------------------------------------------------------------------------

from hyperliquid.api import API
from .fake_info_responses import get_response


@pytest.fixture(autouse=True)
def stub_hyperliquid_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the API layer with deterministic canned responses."""
    def fake_post(self: API, url_path: str, payload: Dict[str, Any] | None = None) -> Any:
        if url_path != "/info":
            raise RuntimeError(f"Unexpected URL path {url_path!r} in fake API layer")
        return get_response(payload or {})
    monkeypatch.setattr(API, "post", fake_post)

# ---------------------------------------------------------------------------
# Pytest configuration
# ---------------------------------------------------------------------------

def pytest_addoption(parser: pytest.Parser) -> None:
    """Register stub options so pytest does not require optional plugins."""
    parser.addoption("--record-mode", action="store", default="none", help="Stub option for pytest-recording")
    parser.addoption("--cov", action="append", default=[], help="Stub option for pytest-cov")
    parser.addoption("--cov-report", action="append", default=[], help="Stub option for pytest-cov")

def pytest_configure(config: pytest.Config) -> None:
    """Document markers and disable doctests for CI safety."""
    config.addinivalue_line("markers", "vcr: compatibility marker for cassette-backed tests")
    config.option.doctestmodules = False  # type: ignore[attr-defined]
    config.option.doctest_continue_on_failure = False  # type: ignore[attr-defined]

def pytest_ignore_collect(path, config):  # type: ignore[override]
    """Skip doctest collection for non-test .py files."""
    try:
        parts = Path(str(path)).parts
    except TypeError:
        return False
    return "tests" not in parts and Path(str(path)).suffix == ".py"
