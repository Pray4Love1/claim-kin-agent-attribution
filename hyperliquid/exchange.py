import copy
import json
import logging
import secrets
from typing import TYPE_CHECKING, Any as TypingAny

if TYPE_CHECKING:  # pragma: no cover - import for type checking only
    from eth_account.signers.local import LocalAccount
else:  # pragma: no cover - runtime fallback when eth-account is unavailable
    LocalAccount = TypingAny  # type: ignore[misc,assignment]

from hyperliquid.api import API
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL
from hyperliquid.utils.signing import (
    CancelByCloidRequest,
    CancelRequest,
    ModifyRequest,
    OidOrCloid,
    OrderRequest,
    OrderType,
    OrderWire,
    ScheduleCancelAction,
    float_to_usd_int,
    get_l1_action_data,
    get_timestamp_ms,
    order_request_to_order_wire,
    order_wires_to_order_action,
    sign_agent,
    sign_approve_builder_fee,
    sign_convert_to_multi_sig_user_action,
    sign_l1_action,
    sign_multi_sig_action,
    sign_send_asset_action,
    sign_spot_transfer_action,
    sign_token_delegate_action,
    sign_usd_class_transfer_action,
    sign_usd_transfer_action,
    sign_withdraw_from_bridge_action,
)
from hyperliquid.utils.types import (
    Any,
    BuilderInfo,
    Cloid,
    Dict,
    List,
    Meta,
    Optional,
    PerpDexSchemaInput,
    SpotMeta,
    Tuple,
)


class Exchange(API):
    # Default Max Slippage for Market Orders 5%
    DEFAULT_SLIPPAGE = 0.05

    def __init__(
        self,
        wallet: LocalAccount,
        base_url: Optional[str] = None,
        meta: Optional[Meta] = None,
        vault_address: Optional[str] = None,
        account_address: Optional[str] = None,
        spot_meta: Optional[SpotMeta] = None,
        perp_dexs: Optional[List[str]] = None,
        timeout: Optional[float] = None,
    ):
        super().__init__(base_url, timeout)
        self.wallet = wallet
        self.vault_address = vault_address
        self.account_address = account_address
        self.info = Info(base_url, True, meta, spot_meta, perp_dexs, timeout)
        self.expires_after: Optional[int] = None
        self._unsigned_actions: Dict[str, List[Dict[str, Any]]] = {}

    def _post_action(self, action, signature, nonce):
        payload = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": self.vault_address if action["type"] not in ["usdClassTransfer", "sendAsset"] else None,
            "expiresAfter": self.expires_after,
        }
        logging.debug(payload)
        return self.post("/exchange", payload)

    def _slippage_price(
        self,
        name: str,
        is_buy: bool,
        slippage: float,
        px: Optional[float] = None,
    ) -> float:
        coin = self.info.name_to_coin[name]
        if not px:
            # Get midprice
            px = float(self.info.all_mids()[coin])

        asset = self.info.coin_to_asset[coin]
        # spot assets start at 10000
        is_spot = asset >= 10_000

        # Calculate Slippage
        px *= (1 + slippage) if is_buy else (1 - slippage)
        # We round px to 5 significant figures and 6 decimals for perps, 8 decimals for spot
        return round(float(f"{px:.5g}"), (6 if not is_spot else 8) - self.info.asset_to_sz_decimals[asset])

    # expires_after will cause actions to be rejected after that timestamp in milliseconds
    # expires_after is not supported on user_signed actions (e.g. usd_transfer) and must be None in order for those
    # actions to work.
    def set_expires_after(self, expires_after: Optional[int]) -> None:
        self.expires_after = expires_after

    def bulk_orders_tx(
        self,
        order_requests: List[OrderRequest],
        builder: Optional[BuilderInfo] = None,
    ) -> Dict[str, Any]:
        """Return the unsigned payload required to submit a batch of orders.

        Mirrors :meth:`bulk_orders` but does not sign or post the action.
        Instead, it returns a dictionary containing:

          - the wire-formatted action,
          - the nonce that must accompany the submission,
          - the EIP-712 typed-data payload for offline signing,
          - the vault address and expires_after context.
        """
        order_wires: List[OrderWire] = [
            order_request_to_order_wire(order, self.info.name_to_asset(order["coin"]))
            for order in order_requests
        ]
        timestamp = get_timestamp_ms()

        if builder:
            builder["b"] = builder["b"].lower()
        order_action = order_wires_to_order_action(order_wires, builder)

        typed_data = get_l1_action_data(
            order_action,
            signature,
            timestamp,
        )

    def bulk_orders_tx(self, order_requests: List[OrderRequest], builder: Optional[BuilderInfo] = None) -> Any:
        """Prepare the typed data payload for a batch of orders without signing.

        This helper mirrors :meth:`bulk_orders` but returns the structured
        ``eth_account`` typed-data payload instead of posting the action. The
        caller can then forward the payload to an external signer, such as a
        hardware wallet, and submit the signed transaction separately.
        """

        order_wires: List[OrderWire] = [
            order_request_to_order_wire(order, self.info.name_to_asset(order["coin"])) for order in order_requests
        ]
        timestamp = get_timestamp_ms()

        if builder:
            builder["b"] = builder["b"].lower()
        order_action = order_wires_to_order_action(order_wires, builder)

        data = get_l1_action_data(
            order_action,
            self.vault_address,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )

        owner_address = getattr(self.wallet, "address", None) or self.account_address
        if owner_address:
            key = owner_address.lower()
            record: Dict[str, Any] = {
                "signer": key,
                "typedData": data,
                "nonce": timestamp,
                "vaultAddress": self.vault_address,
                "expiresAfter": self.expires_after,
                "action": json.loads(json.dumps(order_action)),
            }
            stored_records = self._unsigned_actions.setdefault(key, [])
            stored_records.append(record)

        logging.debug("bulk_orders_tx generated payload: %s", data)
        return data

    def pending_unsigned_actions(self, address: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return unsigned action payloads queued by :meth:`bulk_orders_tx`."""

        if address is None:
            return [copy.copy(record) for records in self._unsigned_actions.values() for record in records]

        key = address.lower()
        return [copy.copy(record) for record in self._unsigned_actions.get(key, [])]

    def clear_unsigned_actions(self, address: Optional[str] = None) -> None:
        """Remove queued unsigned actions for *address* or all actions when omitted."""

        if address is None:
            self._unsigned_actions.clear()
            return

        self._unsigned_actions.pop(address.lower(), None)

    def modify_order(
        self,
        oid: OidOrCloid,
        name: str,
        is_buy: bool,
        sz: float,
        limit_px: float,
        order_type: OrderType,
        reduce_only: bool = False,
        cloid: Optional[Cloid] = None,
    ) -> Any:
        modify: ModifyRequest = {
            "oid": oid,
            "order": {
                "coin": name,
                "is_buy": is_buy,
                "sz": sz,
                "limit_px": limit_px,
                "order_type": order_type,
                "reduce_only": reduce_only,
                "cloid": cloid,
            },
        }
        return self.bulk_modify_orders_new([modify])

    def bulk_modify_orders_new(self, modify_requests: List[ModifyRequest]) -> Any:
        timestamp = get_timestamp_ms()
        modify_wires = [
            {
                "oid": modify["oid"].to_raw() if isinstance(modify["oid"], Cloid) else modify["oid"],
                "order": order_request_to_order_wire(modify["order"], self.info.name_to_asset(modify["order"]["coin"])),
            }
            for modify in modify_requests
        ]

        modify_action = {
            "type": "batchModify",
            "modifies": modify_wires,
        }

        signature = sign_l1_action(
            self.wallet,
            modify_action,
            self.vault_address,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )

        return self._post_action(
            modify_action,
            signature,
            timestamp,
        )

    def market_open(
        self,
        name: str,
        is_buy: bool,
        sz: float,
        px: Optional[float] = None,
        slippage: float = DEFAULT_SLIPPAGE,
        cloid: Optional[Cloid] = None,
        builder: Optional[BuilderInfo] = None,
    ) -> Any:
        # Get aggressive Market Price
        px = self._slippage_price(name, is_buy, slippage, px)
        # Market Order is an aggressive Limit Order IoC
        return self.order(
            name, is_buy, sz, px, order_type={"limit": {"tif": "Ioc"}}, reduce_only=False, cloid=cloid, builder=builder
        )

    def market_close(
        self,
        coin: str,
        sz: Optional[float] = None,
        px: Optional[float] = None,
        slippage: float = DEFAULT_SLIPPAGE,
        cloid: Optional[Cloid] = None,
        builder: Optional[BuilderInfo] = None,
    ) -> Any:
        address: str = self.wallet.address
        if self.account_address:
            address = self.account_address
        if self.vault_address:
            address = self.vault_address
        positions = self.info.user_state(address)["assetPositions"]
        for position in positions:
            item = position["position"]
            if coin != item["coin"]:
                continue
            szi = float(item["szi"])
            if not sz:
                sz = abs(szi)
            is_buy = True if szi < 0 else False
            # Get aggressive Market Price
            px = self._slippage_price(coin, is_buy, slippage, px)
            # Market Order is an aggressive Limit Order IoC
            return self.order(
                coin,
                is_buy,
                sz,
                px,
                order_type={"limit": {"tif": "Ioc"}},
                reduce_only=True,
                cloid=cloid,
                builder=builder,
            )

    def cancel(self, name: str, oid: int) -> Any:
        return self.bulk_cancel([{"coin": name, "oid": oid}])

    def cancel_by_cloid(self, name: str, cloid: Cloid) -> Any:
        return self.bulk_cancel_by_cloid([{"coin": name, "cloid": cloid}])

    def bulk_cancel(self, cancel_requests: List[CancelRequest]) -> Any:
        timestamp = get_timestamp_ms()
        cancel_action = {
            "type": "cancel",
            "cancels": [
                {
                    "a": self.info.name_to_asset(cancel["coin"]),
                    "o": cancel["oid"],
                }
                for cancel in cancel_requests
            ],
        }
        signature = sign_l1_action(
            self.wallet,
            cancel_action,
            self.vault_address,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )

        return self._post_action(
            cancel_action,
            signature,
            timestamp,
        )

    def bulk_cancel_by_cloid(self, cancel_requests: List[CancelByCloidRequest]) -> Any:
        timestamp = get_timestamp_ms()

        cancel_action = {
            "type": "cancelByCloid",
            "cancels": [
                {
                    "asset": self.info.name_to_asset(cancel["coin"]),
                    "cloid": cancel["cloid"].to_raw(),
                }
                for cancel in cancel_requests
            ],
        }
        signature = sign_l1_action(
            self.wallet,
            cancel_action,
            self.vault_address,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )

        return self._post_action(
            cancel_action,
            signature,
            timestamp,
        )

    def schedule_cancel(self, time: Optional[int]) -> Any:
        """Schedules a time (in UTC millis) to cancel all open orders. The time must be at least 5 seconds after the current time.
        Once the time comes, all open orders will be canceled and a trigger count will be incremented. The max number of triggers
        per day is 10. This trigger count is reset at 00:00 UTC.

        Args:
            time (int): if time is not None, then set the cancel time in the future. If None, then unsets any cancel time in the future.
        """
        timestamp = get_timestamp_ms()
        schedule_cancel_action: ScheduleCancelAction = {
            "type": "scheduleCancel",
        }
        if time is not None:
            schedule_cancel_action["time"] = time
        signature = sign_l1_action(
            self.wallet,
            schedule_cancel_action,
            self.vault_address,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            schedule_cancel_action,
            signature,
            timestamp,
        )

    def update_leverage(self, leverage: int, name: str, is_cross: bool = True) -> Any:
        timestamp = get_timestamp_ms()
        update_leverage_action = {
            "type": "updateLeverage",
            "asset": self.info.name_to_asset(name),
            "isCross": is_cross,
            "leverage": leverage,
        }
        signature = sign_l1_action(
            self.wallet,
            update_leverage_action,
            self.vault_address,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            update_leverage_action,
            signature,
            timestamp,
        )

    def update_isolated_margin(self, amount: float, name: str) -> Any:
        timestamp = get_timestamp_ms()
        amount = float_to_usd_int(amount)
        update_isolated_margin_action = {
            "type": "updateIsolatedMargin",
            "asset": self.info.name_to_asset(name),
            "isBuy": True,
            "ntli": amount,
        }
        signature = sign_l1_action(
            self.wallet,
            update_isolated_margin_action,
            self.vault_address,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )

        payload: Dict[str, Any] = {
            "action": order_action,
            "nonce": timestamp,
            "typed_data": typed_data,
            "vault_address": self.vault_address,
            "expires_after": self.expires_after,
        }

        logging.debug("bulk_orders_tx generated payload: %s", payload)
        return payload

    def withdraw_from_bridge(self, amount: float, destination: str) -> Any:
        timestamp = get_timestamp_ms()
        action = {"destination": destination, "amount": str(amount), "time": timestamp, "type": "withdraw3"}
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_withdraw_from_bridge_action(self.wallet, action, is_mainnet)
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def _require_eth_account(self) -> "eth_account":  # pragma: no cover - helper for optional dependency
        try:
            import eth_account  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - dependency missing
            raise RuntimeError("eth-account is required for agent approval flows") from exc
        return eth_account

    def approve_agent(self, name: Optional[str] = None) -> Tuple[Any, str]:
        eth_account = self._require_eth_account()
        agent_key = "0x" + secrets.token_hex(32)
        account = eth_account.Account.from_key(agent_key)
        timestamp = get_timestamp_ms()
        is_mainnet = self.base_url == MAINNET_API_URL
        action = {
            "type": "approveAgent",
            "agentAddress": account.address,
            "agentName": name or "",
            "nonce": timestamp,
        }
        signature = sign_agent(self.wallet, action, is_mainnet)
        if name is None:
            del action["agentName"]

        return (
            self._post_action(
                action,
                signature,
                timestamp,
            ),
            agent_key,
        )

    def approve_builder_fee(self, builder: str, max_fee_rate: str) -> Any:
        timestamp = get_timestamp_ms()

        action = {"maxFeeRate": max_fee_rate, "builder": builder, "nonce": timestamp, "type": "approveBuilderFee"}
        signature = sign_approve_builder_fee(self.wallet, action, self.base_url == MAINNET_API_URL)
        return self._post_action(action, signature, timestamp)

    def convert_to_multi_sig_user(self, authorized_users: List[str], threshold: int) -> Any:
        timestamp = get_timestamp_ms()
        authorized_users = sorted(authorized_users)
        signers = {
            "authorizedUsers": authorized_users,
            "threshold": threshold,
        }
        action = {
            "type": "convertToMultiSigUser",
            "signers": json.dumps(signers),
            "nonce": timestamp,
        }
        signature = sign_convert_to_multi_sig_user_action(self.wallet, action, self.base_url == MAINNET_API_URL)
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_register_token(
        self, token_name: str, sz_decimals: int, wei_decimals: int, max_gas: int, full_name: str
    ) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "spotDeploy",
            "registerToken2": {
                "spec": {"name": token_name, "szDecimals": sz_decimals, "weiDecimals": wei_decimals},
                "maxGas": max_gas,
                "fullName": full_name,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_user_genesis(
        self, token: int, user_and_wei: List[Tuple[str, str]], existing_token_and_wei: List[Tuple[int, str]]
    ) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "spotDeploy",
            "userGenesis": {
                "token": token,
                "userAndWei": [(user.lower(), wei) for (user, wei) in user_and_wei],
                "existingTokenAndWei": existing_token_and_wei,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_enable_freeze_privilege(self, token: int) -> Any:
        return self.spot_deploy_token_action_inner("enableFreezePrivilege", token)

    def spot_deploy_freeze_user(self, token: int, user: str, freeze: bool) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "spotDeploy",
            "freezeUser": {
                "token": token,
                "user": user.lower(),
                "freeze": freeze,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_revoke_freeze_privilege(self, token: int) -> Any:
        return self.spot_deploy_token_action_inner("revokeFreezePrivilege", token)

    def spot_deploy_enable_quote_token(self, token: int) -> Any:
        return self.spot_deploy_token_action_inner("enableQuoteToken", token)

    def spot_deploy_token_action_inner(self, variant: str, token: int) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "spotDeploy",
            variant: {
                "token": token,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_genesis(self, token: int, max_supply: str, no_hyperliquidity: bool) -> Any:
        timestamp = get_timestamp_ms()
        genesis = {
            "token": token,
            "maxSupply": max_supply,
        }
        if no_hyperliquidity:
            genesis["noHyperliquidity"] = True
        action = {
            "type": "spotDeploy",
            "genesis": genesis,
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_register_spot(self, base_token: int, quote_token: int) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "spotDeploy",
            "registerSpot": {
                "tokens": [base_token, quote_token],
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_register_hyperliquidity(
        self, spot: int, start_px: float, order_sz: float, n_orders: int, n_seeded_levels: Optional[int]
    ) -> Any:
        timestamp = get_timestamp_ms()
        register_hyperliquidity = {
            "spot": spot,
            "startPx": str(start_px),
            "orderSz": str(order_sz),
            "nOrders": n_orders,
        }
        if n_seeded_levels is not None:
            register_hyperliquidity["nSeededLevels"] = n_seeded_levels
        action = {
            "type": "spotDeploy",
            "registerHyperliquidity": register_hyperliquidity,
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_set_deployer_trading_fee_share(self, token: int, share: str) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "spotDeploy",
            "setDeployerTradingFeeShare": {
                "token": token,
                "share": share,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def perp_deploy_register_asset(
        self,
        dex: str,
        max_gas: Optional[int],
        coin: str,
        sz_decimals: int,
        oracle_px: str,
        margin_table_id: int,
        only_isolated: bool,
        schema: Optional[PerpDexSchemaInput],
    ) -> Any:
        timestamp = get_timestamp_ms()
        schema_wire = None
        if schema is not None:
            schema_wire = {
                "fullName": schema["fullName"],
                "collateralToken": schema["collateralToken"],
                "oracleUpdater": schema["oracleUpdater"].lower() if schema["oracleUpdater"] is not None else None,
            }
        action = {
            "type": "perpDeploy",
            "registerAsset": {
                "maxGas": max_gas,
                "assetRequest": {
                    "coin": coin,
                    "szDecimals": sz_decimals,
                    "oraclePx": oracle_px,
                    "marginTableId": margin_table_id,
                    "onlyIsolated": only_isolated,
                },
                "dex": dex,
                "schema": schema_wire,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def perp_deploy_set_oracle(
        self,
        dex: str,
        oracle_pxs: Dict[str, str],
        all_mark_pxs: List[Dict[str, str]],
        external_perp_pxs: Dict[str, str],
    ) -> Any:
        timestamp = get_timestamp_ms()
        oracle_pxs_wire = sorted(list(oracle_pxs.items()))
        mark_pxs_wire = [sorted(list(mark_pxs.items())) for mark_pxs in all_mark_pxs]
        external_perp_pxs_wire = sorted(list(external_perp_pxs.items()))
        action = {
            "type": "perpDeploy",
            "setOracle": {
                "dex": dex,
                "oraclePxs": oracle_pxs_wire,
                "markPxs": mark_pxs_wire,
                "externalPerpPxs": external_perp_pxs_wire,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def c_signer_unjail_self(self) -> Any:
        return self.c_signer_inner("unjailSelf")

    def c_signer_jail_self(self) -> Any:
        return self.c_signer_inner("jailSelf")

    def c_signer_inner(self, variant: str) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "CSignerAction",
            variant: None,
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def submit_signed_action(
        self,
        action: Dict[str, Any],
        signature: Dict[str, Any],
        nonce: int,
    ) -> Any:
        """Submit an externally signed action payload to the exchange API."""
        return self._post_action(action, signature, nonce)
