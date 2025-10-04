"""Utilities for generating Codex phantom bot sessions.

This module builds on the existing signing helpers to produce fully
self-described payloads for Codex phantom agents.  The helpers expose a
single public function, :func:`prepare_phantom_session`, which computes the
underlying action hash, wraps it in the phantom agent structure expected by the
Hyperliquid exchange, and returns a serialisable view that can be forwarded to
external signers or orchestration tooling.
"""
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:  # pragma: no cover - dependency guaranteed in production but optional in tests
    from eth_utils import to_hex
except ImportError:  # pragma: no cover - make failure explicit when dependency missing
    def to_hex(value: bytes) -> str:  # type: ignore[override]
        raise RuntimeError("eth-utils is required to format phantom bot payloads")

from hyperliquid.utils.signing import (
    action_hash,
    construct_phantom_agent,
    l1_payload,
)


def _convert_bytes(value: Any) -> Any:
    """Recursively convert ``bytes`` values to hex strings for JSON serialisation."""

    if isinstance(value, (bytes, bytearray)):
        return to_hex(value)
    if isinstance(value, dict):
        return {key: _convert_bytes(inner) for key, inner in value.items()}
    if isinstance(value, (list, tuple)):
        return [_convert_bytes(inner) for inner in value]
    return value


@dataclass(frozen=True)
class PhantomBotSession:
    """Bundle of data describing a Codex phantom bot session.

    The dataclass keeps both the raw phantom agent payload (with ``bytes``
    connection identifiers) and a JSON-friendly representation accessible via
    :meth:`as_dict`.
    """

    action: Dict[str, Any]
    phantom_agent: Dict[str, Any]
    typed_payload: Dict[str, Any]
    action_hash_bytes: bytes
    nonce: int
    vault_address: Optional[str]
    expires_after: Optional[int]
    is_mainnet: bool

    @property
    def connection_id_hex(self) -> str:
        """Return the phantom agent connection ID as a hex string."""

        return to_hex(self.phantom_agent["connectionId"])

    @property
    def action_hash_hex(self) -> str:
        """Return the action hash as a hex string."""

        return to_hex(self.action_hash_bytes)

    def as_dict(self, *, include_typed_data: bool = True, include_action: bool = True) -> Dict[str, Any]:
        """Return a JSON-friendly view of the session.

        Parameters
        ----------
        include_typed_data:
            When ``True`` (the default) the EIP-712 typed payload is included in
            the output after converting ``bytes`` fields to hex strings.
        include_action:
            When ``True`` (the default) the original action is included.  The
            action is round-tripped through :func:`json.dumps` to guarantee that
            it is serialisable before returning the summary.
        """

        summary: Dict[str, Any] = {
            "nonce": self.nonce,
            "vaultAddress": self.vault_address,
            "expiresAfter": self.expires_after,
            "isMainnet": self.is_mainnet,
            "actionHash": self.action_hash_hex,
            "phantomAgent": {
                "source": self.phantom_agent["source"],
                "connectionId": self.connection_id_hex,
            },
        }

        if include_action:
            summary["action"] = json.loads(json.dumps(self.action))

        if include_typed_data:
            summary["typedData"] = _convert_bytes(self.typed_payload)

        return summary


def prepare_phantom_session(
    action: Dict[str, Any],
    vault_address: Optional[str],
    nonce: int,
    expires_after: Optional[int],
    *,
    is_mainnet: bool,
) -> PhantomBotSession:
    """Create a :class:`PhantomBotSession` for *action*.

    Parameters
    ----------
    action:
        The structured Hyperliquid action payload to be signed.
    vault_address:
        Optional vault address participating in the action.
    nonce:
        Monotonic timestamp (in milliseconds) that prevents replay.
    expires_after:
        Optional timestamp (milliseconds) after which the action is invalid.
    is_mainnet:
        ``True`` when preparing data for mainnet, ``False`` for testnet.
    """

    action_copy = deepcopy(action)
    hash_bytes = action_hash(action_copy, vault_address, nonce, expires_after)
    phantom_agent = construct_phantom_agent(hash_bytes, is_mainnet)
    typed_payload = l1_payload(phantom_agent.copy())

    return PhantomBotSession(
        action=action_copy,
        phantom_agent=phantom_agent,
        typed_payload=typed_payload,
        action_hash_bytes=hash_bytes,
        nonce=nonce,
        vault_address=vault_address,
        expires_after=expires_after,
        is_mainnet=is_mainnet,
    )


__all__ = ["PhantomBotSession", "prepare_phantom_session"]