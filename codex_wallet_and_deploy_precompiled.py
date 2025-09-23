"""Utility for deploying the KinRoyaltyPaymaster precompiled contract.

This helper connects to a Hyperliquid-compatible RPC endpoint, loads a wallet
from a private key, and deploys the precompiled bytecode with the keeper, vault
address, and royalty basis points you specify.

Examples:
    # Load PRIVATE_KEY from the environment, deploy against the default RPC
    python codex_wallet_and_deploy_precompiled.py \
        --target-vault 0x000000000000000000000000000000000000dEaD \
        --royalty-bps 800

    # Provide a custom RPC endpoint and explicit keeper address
    python codex_wallet_and_deploy_precompiled.py \
        --rpc-url https://rpc.hyperliquid.xyz/evm \
        --keeper 0xYourKeeperAddress \
        --target-vault 0xAnotherVault \
        --royalty-bps 1000

If ``PRIVATE_KEY`` is not set the script falls back to prompting securely via
``getpass``.
"""

from __future__ import annotations

import argparse
import os
import sys
from getpass import getpass
from typing import Any, Dict

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3
from web3.exceptions import TransactionNotFound

# NOTE: The bytecode below originates from the KinRoyaltyPaymaster precompiled
# artifact. Retain it verbatim to ensure deployments remain deterministic.
BYTECODE = (
    "608060405234801561001057600080fd5b506040516104f63803806104f683398181016040528101906100329190610082565b8060008190555033600081815260200190815260200160002081905550806000819055506100e1806100636000396000f3fe6080604052600436106100345760003560e01c8063103c6b49146100395780638da5cb5b14610057578063f7c618c114610075575b600080fd5b610041610093565b60405161004e91906101a3565b60405180910390f35b61005f6100a7565b60405161006c91906101a3565b60405180910390f35b61007d6100bb565b60405161008a91906101a3565b60405180910390f35b60005481565b600080546001019055565b6000805460ff166001146100c857600080fd5b6001546000805460ff19166001179055600181905550565b60008054905090565b6100f8816100e9565b82525050565b600060208201905061011360008301846100ef565b92915050565b6000604051905090565b600067ffffffffffffffff82111561013b5761013a610134565b5b6101448261010d565b9050602081019050919050565b82818337600083830152505050565b60006101738261014e565b915061017e8361014e565b925082820190508082111561019657610195610134565b5b92915050565b6000819050919050565b6101b08161019d565b81146101bb57600080fd5b50565b6000813590506101cd816101a7565b92915050565b600080604083850312156101e9576101e86101a2565b5b60006101f7858286016101be565b9250506020610208858286016101be565b915050925092905056fea26469706673582212202ae0f456b8c19d61a31b47b04648197e0301049e6c3b43abcb503504cb3ea02e64736f6c63430008140033"
)

ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "_keeper", "type": "address"},
            {"internalType": "address", "name": "_targetVault", "type": "address"},
            {"internalType": "uint256", "name": "_royaltyBps", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
        "type": "constructor",
    }
]

DEFAULT_RPC_URL = "https://rpc.hyperliquid.xyz/evm"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy the KinRoyaltyPaymaster precompiled contract",
    )
    parser.add_argument(
        "--rpc-url",
        default=DEFAULT_RPC_URL,
        help="EVM-compatible RPC endpoint (default: %(default)s)",
    )
    parser.add_argument(
        "--keeper",
        help="Keeper address that will control the royalty paymaster (defaults to the signer)",
    )
    parser.add_argument(
        "--target-vault",
        required=True,
        help="Vault address that should receive royalty distributions",
    )
    parser.add_argument(
        "--royalty-bps",
        type=int,
        required=True,
        help="Royalty percentage expressed in basis points (1% = 100)",
    )
    parser.add_argument(
        "--private-key",
        help="Private key used for signing. If omitted the script checks PRIVATE_KEY or prompts securely.",
    )
    parser.add_argument(
        "--gas-price",
        type=int,
        help="Explicit gas price in wei. If omitted the script derives EIP-1559 fees when available.",
    )
    return parser.parse_args(argv)


def load_account(parsed_args: argparse.Namespace) -> LocalAccount:
    candidate = (
        parsed_args.private_key
        or os.environ.get("PRIVATE_KEY")
        or os.environ.get("secret_key")
    )

    if not candidate:
        candidate = getpass("Enter your PRIVATE_KEY (hidden input): ").strip()

    try:
        account = Account.from_key(candidate)
    except ValueError as exc:  # raised when the key format is invalid
        raise SystemExit(f"Failed to load account from private key: {exc}") from exc

    return account


def ensure_checksum_address(w3: Web3, raw: str, *, label: str) -> str:
    try:
        return w3.to_checksum_address(raw)
    except ValueError as exc:
        raise SystemExit(f"Invalid {label} address '{raw}': {exc}") from exc


def detect_fee_fields(w3: Web3, explicit_gas_price: int | None) -> Dict[str, int]:
    if explicit_gas_price is not None:
        if explicit_gas_price <= 0:
            raise SystemExit("--gas-price must be a positive integer when supplied")
        return {"gasPrice": explicit_gas_price}

    latest_block: Dict[str, Any] = w3.eth.get_block("latest")
    base_fee = latest_block.get("baseFeePerGas")

    if base_fee is None:
        # Legacy networks without base fee still accept a gas price.
        return {"gasPrice": w3.eth.gas_price}

    priority_fee = w3.eth.max_priority_fee
    if priority_fee is None:
        priority_fee = Web3.to_wei(2, "gwei")

    # Apply a headroom multiplier (2x base fee) to minimize replacement.
    max_fee = base_fee * 2 + priority_fee
    return {
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": priority_fee,
    }


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    w3 = Web3(Web3.HTTPProvider(args.rpc_url))

    if not w3.is_connected():
        raise SystemExit(f"Unable to reach RPC endpoint at {args.rpc_url}")

    account = load_account(args)
    keeper_address = ensure_checksum_address(
        w3,
        args.keeper or account.address,
        label="keeper",
    )
    target_vault_address = ensure_checksum_address(
        w3,
        args.target_vault,
        label="target vault",
    )

    if args.royalty_bps < 0:
        raise SystemExit("--royalty-bps must be a non-negative integer")

    print("🔐 Wallet loaded:", account.address)
    print("🔗 RPC endpoint:", args.rpc_url)
    print("👷 Keeper:", keeper_address)
    print("🏦 Target vault:", target_vault_address)
    print("💸 Royalty (bps):", args.royalty_bps)

    contract = w3.eth.contract(abi=ABI, bytecode=BYTECODE)
    nonce = w3.eth.get_transaction_count(account.address)
    fee_fields = detect_fee_fields(w3, args.gas_price)

    txn_dict = contract.constructor(
        keeper_address,
        target_vault_address,
        args.royalty_bps,
    ).build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "chainId": w3.eth.chain_id,
            **fee_fields,
        }
    )

    gas_estimate = w3.eth.estimate_gas({**txn_dict, "from": account.address})
    txn_dict["gas"] = gas_estimate

    signed_txn = account.sign_transaction(txn_dict)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

    print("🚀 Deployment transaction submitted!")
    print("📝 Transaction hash:", tx_hash.hex())

    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    except TransactionNotFound:
        print("⚠️ Transaction not found yet. Check the explorer for status updates.")
        return

    contract_address = receipt.contractAddress
    if contract_address:
        print("✅ Contract deployed at:", contract_address)
    else:
        print("⚠️ Deployment transaction mined but contract address missing in receipt.")


if __name__ == "__main__":
    main(sys.argv[1:])
