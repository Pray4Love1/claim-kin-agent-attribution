from hyperliquid.api import API
from hyperliquid.utils.types import (
    Any,
    Callable,
    Cloid,
    List,
    Meta,
    Optional,
    SpotMeta,
    SpotMetaAndAssetCtxs,
    Subscription,
    cast,
)
from hyperliquid.websocket_manager import WebsocketManager


class Info(API):
    def __init__(
        self,
        base_url: Optional[str] = None,
        skip_ws: Optional[bool] = False,
        meta: Optional[Meta] = None,
        spot_meta: Optional[SpotMeta] = None,
        perp_dexs: Optional[List[str]] = None,
        timeout: Optional[float] = None,
    ):
        super().__init__(base_url, timeout)
        self.ws_manager: Optional[WebsocketManager] = None
        if not skip_ws:
            self.ws_manager = WebsocketManager(self.base_url)
            self.ws_manager.start()

        if spot_meta is None:
            spot_meta = self.spot_meta()

        self.coin_to_asset = {}
        self.name_to_coin = {}
        self.asset_to_sz_decimals = {}

        for spot_info in spot_meta["universe"]:
            asset = spot_info["index"] + 10000
            self.coin_to_asset[spot_info["name"]] = asset
            self.name_to_coin[spot_info["name"]] = spot_info["name"]
            base, quote = spot_info["tokens"]
            base_info = spot_meta["tokens"][base]
            quote_info = spot_meta["tokens"][quote]
            self.asset_to_sz_decimals[asset] = base_info["szDecimals"]
            name = f'{base_info["name"]}/{quote_info["name"]}'
            if name not in self.name_to_coin:
                self.name_to_coin[name] = spot_info["name"]

        perp_dex_to_offset = {"": 0}
        if perp_dexs is None:
            perp_dexs = [""]
        else:
            for i, perp_dex in enumerate(self.perp_dexs()[1:]):
                perp_dex_to_offset[perp_dex["name"]] = 110000 + i * 10000

        for perp_dex in perp_dexs:
            offset = perp_dex_to_offset[perp_dex]
            if perp_dex == "" and meta is not None:
                self.set_perp_meta(meta, 0)
            else:
                fresh_meta = self.meta(dex=perp_dex)
                self.set_perp_meta(fresh_meta, offset)

    def set_perp_meta(self, meta: Meta, offset: int) -> Any:
        for asset, asset_info in enumerate(meta["universe"]):
            asset += offset
            self.coin_to_asset[asset_info["name"]] = asset
            self.name_to_coin[asset_info["name"]] = asset_info["name"]
            self.asset_to_sz_decimals[asset] = asset_info["szDecimals"]

    def disconnect_websocket(self):
        if self.ws_manager:
            self.ws_manager.stop()
        else:
            raise RuntimeError("Cannot call disconnect_websocket since skip_ws was used")
    def user_state(self, user: str) -> Any:
        return self.post("/info", {"type": "userState", "user": user})

    def all_vaults(self) -> Any:
        return self.post("/info", {"type": "allVaults"})

    def fills(self, user: str, include_deposits: Optional[bool] = None) -> Any:
        body: Any = {"type": "userFills", "user": user}
        if include_deposits is not None:
            body["includeDeposits"] = include_deposits
        return self.post("/info", body)

    def portfolio(self, user: str) -> Any:
        return self.post("/info", {"type": "portfolio", "user": user})

    def l2_snapshot(self, coin: str) -> Any:
        return self.post("/info", {"type": "l2Snapshot", "coin": coin})

    def open_orders(self, user: str) -> Any:
        return self.post("/info", {"type": "openOrders", "user": user})

    def historical_orders(self, user: str) -> Any:
        return self.post("/info", {"type": "historicalOrders", "user": user})

    def user_role(self, user: str) -> Any:
        return self.post("/info", {"type": "userRole", "user": user})

    def user_rate_limit(self, user: str) -> Any:
        return self.post("/info", {"type": "userRateLimit", "user": user})
    def extra_agents(self, user: str) -> Any:
        return self.post("/info", {"type": "extraAgents", "user": user})

    def equity(self, user: str) -> Any:
        return self.post("/info", {"type": "equity", "user": user})

    def performance(self, user: str) -> Any:
        return self.post("/info", {"type": "performance", "user": user})

    def twap_fills(self, user: str) -> Any:
        return self.post("/info", {"type": "twapFills", "user": user})

    def account_role(self, user: str) -> Any:
        return self.post("/info", {"type": "accountRole", "user": user})

    def api_rate_limit(self, user: str) -> Any:
        return self.post("/info", {"type": "apiRateLimit", "user": user})

    def delegator_events(self, user: str) -> Any:
        return self.post("/info", {"type": "delegatorEvents", "user": user})

    def funding_history(self, coin: str) -> Any:
        return self.post("/info", {"type": "fundingHistory", "coin": coin})

    def user_funding_history(self, user: str) -> Any:
        return self.post("/info", {"type": "userFundingHistory", "user": user})
