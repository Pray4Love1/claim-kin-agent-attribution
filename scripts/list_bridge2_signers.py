"""Fetch the current Bridge2 validator lock set and finalizer whitelist."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, List
from urllib.error import URLError
from urllib.request import Request, urlopen

DEFAULT_RPC_URL = "https://rpc.hyperliquid.xyz/evm"
BRIDGE2_ADDRESS = "0x2Df1c51E09aECF9cacB7bc98cB1742757f163dF7"


@dataclass
class RpcClient:
    """Minimal JSON-RPC helper that honours the platform proxy configuration."""

    url: str

    def call(self, method: str, params: Iterable[object]) -> dict:
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": list(params)}).encode()
        request = Request(self.url, data=payload, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        if "error" in data:
            raise RuntimeError(f"RPC error: {data['error']}")
        return data["result"]


def _sha3_selector(signature: str) -> str:
    digest = hashlib.sha3_256(signature.encode("ascii")).hexdigest()
    return "0x" + digest[:8]


def _abi_address(value: str) -> str:
    return value.rjust(64, "0")


def _decode_address_array(data_hex: str) -> List[str]:
    if data_hex.startswith("0x"):
        data_hex = data_hex[2:]
    data = bytes.fromhex(data_hex)
    if len(data) < 64:
        raise ValueError("Result too short for dynamic array")
    offset = int.from_bytes(data[:32], "big")
    if offset + 32 > len(data):
        raise ValueError("Offset exceeds payload length")
    length = int.from_bytes(data[offset : offset + 32], "big")
    items: List[str] = []
    cursor = offset + 32
    for _ in range(length):
        if cursor + 32 > len(data):
            raise ValueError("Truncated array item")
        word = data[cursor : cursor + 32]
        items.append("0x" + word[12:].hex())
        cursor += 32
    return items


def _decode_uint(data_hex: str) -> int:
    if data_hex.startswith("0x"):
        data_hex = data_hex[2:]
    data = bytes.fromhex(data_hex.rjust(64, "0"))
    return int.from_bytes(data, "big")


def _decode_bool(data_hex: str) -> bool:
    return _decode_uint(data_hex) != 0


def install_proxy_from_env() -> None:
    import os
    proxies = {}
    for scheme in ('http', 'https'):
        value = os.environ.get(f'{scheme}_proxy') or os.environ.get(f'{scheme.upper()}_PROXY')
        if value:
            proxies[scheme] = value
    if not proxies:
        return
    from urllib.request import ProxyHandler, build_opener, install_opener
    handler = ProxyHandler(proxies)
    install_opener(build_opener(handler))


def fetch_lockers(client: RpcClient) -> List[str]:
    selector = _sha3_selector("getLockersVotingLock()")
    result = client.call("eth_call", [{"to": BRIDGE2_ADDRESS, "data": selector}, "latest"])
    return _decode_address_array(result)


def fetch_locker_threshold(client: RpcClient) -> int:
    selector = _sha3_selector("lockerThreshold()")
    result = client.call("eth_call", [{"to": BRIDGE2_ADDRESS, "data": selector}, "latest"])
    return _decode_uint(result)


def fetch_finalizer_flags(client: RpcClient, addresses: Iterable[str]) -> List[str]:
    selector = _sha3_selector("finalizers(address)")
    finalizers: List[str] = []
    for address in addresses:
        arg = selector + _abi_address(address[2:])
        result = client.call("eth_call", [{"to": BRIDGE2_ADDRESS, "data": arg}, "latest"])
        if _decode_bool(result):
            finalizers.append(address)
    return finalizers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpc-url", default=DEFAULT_RPC_URL, help="JSON-RPC endpoint for Hyperliquid EVM")
    args = parser.parse_args()

    install_proxy_from_env()
    client = RpcClient(args.rpc_url)

    try:
        lockers = fetch_lockers(client)
        threshold = fetch_locker_threshold(client)
        finalizers = fetch_finalizer_flags(client, lockers)
    except URLError as exc:
        print(f"Network error while contacting {args.rpc_url}: {exc}")
        return 2
    except Exception as exc:  # pragma: no cover - defensive guard for unexpected RPC issues
        print(f"Failed to query Bridge2: {exc}")
        return 1

    print("Bridge2 voting lock addresses:")
    for index, address in enumerate(lockers):
        marker = " (finalizer)" if address in finalizers else ""
        print(f"  {index:02d}: {address}{marker}")
    print()
    print(f"Locker threshold: {threshold}")
    print(f"Finalizers found: {len(finalizers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())