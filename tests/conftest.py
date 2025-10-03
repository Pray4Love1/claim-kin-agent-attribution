"""Test configuration for compatibility with upstream pytest options.

This repository's pytest configuration references optional plugins such as
``pytest-recording`` and ``pytest-cov``. Those plugins are not available in the
execution environment used for automated evaluation, which causes pytest to
abort before running any tests because it does not recognize the associated
command line flags.  To keep the suite runnable we provide minimal shims that
register the expected options while deliberately doing nothing with their
values.
"""

from __future__ import annotations

import pytest


@pytest.hookimpl
def pytest_addoption(parser: pytest.Parser) -> None:
    """Register no-op CLI options used by optional pytest plugins.

    The project enables ``--record-mode`` (from ``pytest-recording``) and
    ``--cov``/``--cov-report`` (from ``pytest-cov``) in the ``addopts``
    configuration.  When those plugins are unavailable pytest raises an error
    before the tests are executed.  By defining matching options here we allow
    the CLI parsing stage to succeed so the rest of the test suite can run.
    """

    group = parser.getgroup("compatibility")
    group.addoption(
        "--record-mode",
        action="store",
        default="once",
        help="Compatibility shim for pytest-recording. Ignored when the plugin"
        " is unavailable.",
    )
    group.addoption(
        "--cov",
        action="append",
        default=[],
        metavar="MODULE",
        help="Compatibility shim for pytest-cov. No coverage will be collected"
        " in this environment.",
    )
    group.addoption(
        "--cov-report",
        action="append",
        default=[],
        metavar="TYPE",
        help="Compatibility shim for pytest-cov. Reports are not generated",
    )
