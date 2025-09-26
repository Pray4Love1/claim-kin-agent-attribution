import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register stub options used by optional plugins in upstream project."""

    parser.addoption("--record-mode", action="store", default="none", help="Stub option for pytest-recording")
    parser.addoption("--cov", action="append", default=[], help="Stub option for pytest-cov")
    parser.addoption("--cov-report", action="append", default=[], help="Stub option for pytest-cov")
