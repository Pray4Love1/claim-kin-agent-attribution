#!/usr/bin/env python3
"""Codex vault discovery tool for SolaraKin vaults (Keeper-only use)."""

from hyperliquid.info import Info
from hyperliquid.utils import constants
from pprint import pprint


def main():
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    payload = {"type": "vaults"}
    vaults = info.post("/info", payload)
    pprint(vaults)


if __name__ == "__main__":
    main()
