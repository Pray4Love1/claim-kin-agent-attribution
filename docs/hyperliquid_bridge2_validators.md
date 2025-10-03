# Hyperliquid Bridge 2 validator introspection

The Bridge 2 contract maintains a voting lock of addresses that can co-sign
withdrawal bundles together with a smaller subset of finalizers. Because the
set can rotate, the safest way to obtain the latest participants is to query
Hyperliquid's RPC directly.

Use the helper below to retrieve the data from an environment with network
access:

```bash
python scripts/list_bridge2_signers.py --rpc-url https://rpc.hyperliquid.xyz/evm
```

The script performs three read-only calls:

1. `getLockersVotingLock()` – returns the full address array stored on chain.
2. `lockerThreshold()` – indicates how many signatures are required.
3. `finalizers(address)` – filters the array to the whitelisted finalizers.

The output lists every locker with a `(finalizer)` suffix when the address can
publish `batchedFinalizeWithdrawals`. Run the command again whenever you need
updated membership information.
