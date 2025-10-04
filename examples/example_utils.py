import getpass
import json
import json
import os
import os


from typing import Any, Dict

import eth_account
import eth_account
from eth_account.signers.local import LocalAccount
from eth_account.signers.local import LocalAccount


from hyperliquid.exchange import Exchange
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.info import Info




class _WalletAdapter:
    """Adapter that normalises signatures from :mod:`eth_account` for the SDK."""

    def __init__(self, account: LocalAccount):
        self._account = account
        self.address = account.address

    def __getattr__(self, item: str) -> Any:
        return getattr(self._account, item)

    def sign_message(self, structured_data: Any) -> Dict[str, Any]:
        signed = self._account.sign_message(structured_data)

        if isinstance(signed, dict):
            return signed

        if hasattr(signed, "to_dict"):
            return signed.to_dict()

        if all(hasattr(signed, attr) for attr in ("r", "s", "v")):
            return {"r": signed.r, "s": signed.s, "v": signed.v}

        if isinstance(signed, (bytes, bytearray)):
            if len(signed) != 65:
                raise ValueError("Unexpected signature length returned from sign_message")
            r_bytes = signed[:32]
            s_bytes = signed[32:64]
            v_byte = signed[64]
            v_value = v_byte if isinstance(v_byte, int) else int.from_bytes(bytes([v_byte]), "big")
            return {
                "r": int.from_bytes(r_bytes, "big"),
                "s": int.from_bytes(s_bytes, "big"),
                "v": v_value,
            }

        raise TypeError(f"Unsupported signature type returned from sign_message: {type(signed)!r}")


def setup(base_url=None, skip_ws=False, perp_dexs=None):
def setup(base_url=None, skip_ws=False, perp_dexs=None):
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path) as f:
    with open(config_path) as f:
        config = json.load(f)
        config = json.load(f)
    account: LocalAccount = eth_account.Account.from_key(get_secret_key(config))
    raw_account: LocalAccount = eth_account.Account.from_key(get_secret_key(config))
    account = _WalletAdapter(raw_account)
    address = config["account_address"]
    address = config["account_address"]
    if address == "":
    if address == "":
        address = account.address
        address = account.address
    print("Running with account address:", address)
    print("Running with account address:", address)
    if address != account.address:
    if address != account.address:
        print("Running with agent address:", account.address)
        print("Running with agent address:", account.address)
    info = Info(base_url, skip_ws, perp_dexs=perp_dexs)
    info = Info(base_url, skip_ws, perp_dexs=perp_dexs)
    user_state = info.user_state(address)
    user_state = info.user_state(address)
    spot_user_state = info.spot_user_state(address)
    spot_user_state = info.spot_user_state(address)
    margin_summary = user_state["marginSummary"]
    margin_summary = user_state["marginSummary"]
    if float(margin_summary["accountValue"]) == 0 and len(spot_user_state["balances"]) == 0:
    if float(margin_summary["accountValue"]) == 0 and len(spot_user_state["balances"]) == 0:
        print("Not running the example because the provided account has no equity.")
        print("Not running the example because the provided account has no equity.")
        url = info.base_url.split(".", 1)[1]
        url = info.base_url.split(".", 1)[1]
        error_string = f"No accountValue:\nIf you think this is a mistake, make sure that {address} has a balance on {url}.\nIf address shown is your API wallet address, update the config to specify the address of your account, not the address of the API wallet."
        error_string = f"No accountValue:\nIf you think this is a mistake, make sure that {address} has a balance on {url}.\nIf address shown is your API wallet address, update the config to specify the address of your account, not the address of the API wallet."
        raise Exception(error_string)
        raise Exception(error_string)
    exchange = Exchange(account, base_url, account_address=address, perp_dexs=perp_dexs)
    exchange = Exchange(account, base_url, account_address=address, perp_dexs=perp_dexs)
    return address, info, exchange
    return address, info, exchange




def get_secret_key(config):
def get_secret_key(config):
    if config["secret_key"]:
    if config["secret_key"]:
        secret_key = config["secret_key"]
        secret_key = config["secret_key"]
    else:
    else:
        keystore_path = config["keystore_path"]
        keystore_path = config["keystore_path"]
        keystore_path = os.path.expanduser(keystore_path)
        keystore_path = os.path.expanduser(keystore_path)
