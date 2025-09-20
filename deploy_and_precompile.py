#!/usr/bin/env python3
"""Deploy helper that precompiles key Python modules before shipping.

The script is intended to run from any working directory. It compiles a set of
Python entrypoints by default, and it accepts optional overrides via the CLI.
"""
from __future__ import annotations

import argparse
import py_compile
import sys
from pathlib import Path
from typing import Iterable, List

SCRIPT_DIR = Path(__file__).resolve().parent

DEFAULT_TARGET_FILENAMES = (
    "codex_runner_f303.py",
    "deploy_agent_wallet.py",
    "find_kinvaults.py",
    "find_solara_vaults.py",
    "hyperliquid/__init__.py",
    "hyperliquid/api.py",
    "hyperliquid/exchange.py",
    "hyperliquid/info.py",
    "hyperliquid/utils/__init__.py",
    "hyperliquid/utils/constants.py",
    "hyperliquid/utils/error.py",
    "hyperliquid/utils/signing.py",
    "hyperliquid/utils/types.py",
    "hyperliquid/websocket_manager.py",
)

DEFAULT_TARGETS = tuple((SCRIPT_DIR / name).resolve() for name in DEFAULT_TARGET_FILENAMES)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "targets",
        nargs="*",
        help="Optional paths to Python files that should be precompiled instead of the defaults.",
    )
    return parser.parse_args()


def normalize_targets(targets: Iterable[str]) -> List[Path]:
    """Convert target strings to absolute ``Path`` instances."""
    normalized: List[Path] = []
    for target in targets:
        normalized.append(Path(target).expanduser().resolve())
    return normalized


def gather_targets(target_args: Iterable[str]) -> List[Path]:
    if target_args:
        return normalize_targets(target_args)
    return list(DEFAULT_TARGETS)


def precompile(target: Path) -> bool:
    try:
        py_compile.compile(str(target), dfile=str(target), doraise=True)
    except (py_compile.PyCompileError, OSError) as exc:
        print(f"❌ Failed to precompile {target}: {exc}")
        return False
    else:
        print(f"✅ Precompiled {target}")
        return True


def main() -> int:
    args = parse_args()
    targets = gather_targets(args.targets)

    if not targets:
        print("No targets to precompile.", file=sys.stderr)
        return 1

    status = 0
    for target in targets:
        if not precompile(target):
            status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
