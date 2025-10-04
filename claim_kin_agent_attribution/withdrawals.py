"""Helpers for performing Hyperliquid withdrawals via Codex tooling."""
from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Tuple, TYPE_CHECKING

from eth_account import Account

if TYPE_CHECKING:  # pragma: no cover - typing only
    from eth_account.signers.local import LocalAccount
    from hyperliquid.exchange import Exchange
else:  # pragma: no cover - runtime fallback when optional deps are missing
    LocalAccount = Any  # type: ignore[assignment]
    Exchange = Any  # type: ignore[assignment]

DEFAULT_DESTINATION = "0x996994D2914DF4eEE6176FD5eE152e2922787EE7"


def _load_env_file(env: MutableMapping[str, str]) -> None:
    """Populate ``env`` from a ``.env`` file when present."""

    env_path = Path(".env")
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key and key not in env:
            env[key] = value


def _get_env() -> MutableMapping[str, str]:
    """Expose ``os.environ`` separately to simplify testing."""

    env = os.environ
    _load_env_file(env)
    return env


def load_api_wallet(env: Mapping[str, str] | None = None) -> Tuple[LocalAccount, str]:
    """Return the API wallet account and the trading address it controls.

    Parameters
    ----------
    env:
        Optional mapping used to resolve environment variables. When omitted
        ``os.environ`` (after ``load_dotenv``) is used.

    Returns
    -------
    tuple
        The instantiated ``LocalAccount`` and the Hyperliquid account address
        that the wallet should operate on behalf of.

    Raises
    ------
    RuntimeError
        If no secret key is present in the environment.
    """

    if env is None:
        env = _get_env()

    secret_key = (
        env.get("HL_API_KEY")
        or env.get("HL_SECRET_KEY")
        or env.get("HYPERLIQUID_PRIVATE_KEY")
        or env.get("PRIVATE_KEY")
    )
    if not secret_key:
        raise RuntimeError("Set HL_API_KEY (or HL_SECRET_KEY/HYPERLIQUID_PRIVATE_KEY) before running withdrawals.")

    account = Account.from_key(secret_key)
    account_address = env.get("HL_ACCOUNT_ADDRESS") or account.address
    return account, account_address


def perform_withdrawal(
    amount: Decimal,
    destination: str,
    wallet: LocalAccount,
    *,
    base_url: str | None = None,
    account_address: str,
    exchange_cls: Any = None,
):
    """Submit a withdraw-from-bridge action for ``amount`` USD to ``destination``."""

    if amount <= 0:
        raise ValueError("Withdrawal amount must be positive.")

    if exchange_cls is None:
        from hyperliquid.exchange import Exchange as ExchangeImpl  # pragma: no cover - lazy import
        from hyperliquid.utils.constants import MAINNET_API_URL  # pragma: no cover - lazy import

        exchange_cls = ExchangeImpl
        resolved_base_url = base_url or MAINNET_API_URL
    else:
        resolved_base_url = base_url or "https://api.hyperliquid.xyz"

    exchange = exchange_cls(wallet, resolved_base_url, account_address=account_address)
    return exchange.withdraw_from_bridge(float(amount), destination)


__all__ = [
    "DEFAULT_DESTINATION",
    "load_api_wallet",
    "perform_withdrawal",
]

