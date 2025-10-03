"""Test configuration ensuring compatibility in both local and CI environments.

- Provides no-op shims for pytest plugin options (pytest-cov, pytest-recording).
- Stubs out unavailable dependencies (requests, websocket).
- Adds Hyperliquid API monkeypatching for deterministic responses.
- Disables doctest collection in CI.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import sys
from types import ModuleType
import pytest

# --------------------------------------------------------------------
# Dependency stubs
# --------------------------------------------------------------------
try:
    import requests  # type: ignore
except ModuleNotFoundError:
    class _DummySession:
        def __init__(self) -> None:
            self.headers: Dict[str, str] = {}

        def post(self, url: str, json: Dict[str, Any] | None = None, timeout: float | None = None):
            raise RuntimeError("Network access is disabled in this environment")

    requests = ModuleType("requests")
    requests.Session = _DummySession  # type: ignore[attr-defined]
    requests.HTTPError = RuntimeError  # type: ignore[attr-defined]
    sys.modules["requests"] = requests

try:
    import websocket  # type: ignore
except ModuleNotFoundError:
    class _DummyWebSocketApp:
        def __init__(self, *_args, **_kwargs) -> None:
            self.keep_running = False

        def run_forever(self): return None
        def send(self, _msg: str): return None
        def close(self): return None

    websocket = ModuleType("websocket")
    websocket.WebSocketApp = _DummyWebSocketApp  # type: ignore[attr-defined]
    sys.modules["websocket"] = websocket

# --------------------------------------------------------------------
# Hyperliquid API stub
# --------------------------------------------------------------------
from hyperliquid.api import API
from tests.utils.canned_response import get_response

@pytest.fixture(autouse=True)
def stub_hyperliquid_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the API layer with deterministic canned responses."""
    def fake_post(self: API, url_path: str, payload: Dict[str, Any] | None = None) -> Any:
        if url_path != "/info":
            raise RuntimeError(f"Unexpected URL path {url_path!r} in fake API layer")
        return get_response(payload or {})
    monkeypatch.setattr(API, "post", fake_post)

# --------------------------------------------------------------------
# Pytest plugin option shims
# --------------------------------------------------------------------
@pytest.hookimpl
def pytest_addoption(parser: pytest.Parser) -> None:
    """Register plugin compatibility options for pytest-recording and pytest-cov."""
    group = parser.getgroup("compatibility")
    group.addoption(
        "--record-mode",
        action="store",
        default="once",
        help="Shim for pytest-recording; ignored if plugin missing.",
    )
    group.addoption(
        "--cov",
        action="append",
        default=[],
        metavar="MODULE",
        help="Shim for pytest-cov; no coverage will be collected.",
    )
    group.addoption(
        "--cov-report",
        action="append",
        default=[],
        metavar="TYPE",
        help="Shim for pytest-cov; reports not generated.",
    )

# --------------------------------------------------------------------
# Doctest disabling & marker registration
# --------------------------------------------------------------------
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "vcr: compatibility marker for cassette-backed tests")
    config.option.doctestmodules = False  # type: ignore[attr-defined]
    config.option.doctest_continue_on_failure = False  # type: ignore[attr-defined]

def pytest_ignore_collect(path, config):  # type: ignore[override]
    """Skip doctest collection outside `tests/`."""
    try:
        parts = Path(str(path)).parts
    except TypeError:
        return False
    return "tests" not in parts and Path(str(path)).suffix == ".py"
