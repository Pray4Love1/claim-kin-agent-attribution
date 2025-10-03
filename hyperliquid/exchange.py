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

    def submit_signed_action(
        self,
        action: Dict[str, Any],
        signature: Dict[str, Any],
        nonce: int,
    ) -> Any:
        """Submit an externally signed action payload to the exchange API."""
        return self._post_action(action, signature, nonce)
