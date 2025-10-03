"""Hyperliquid royalty claim generation utilities.

This module reproduces the logic from the "Codex Claim Script" shared in the
task description.  It provides helper functions for constructing the canonical
claim payload, calculating the total royalties owed, and emitting the
corresponding JSON/hash artifacts used for verification.

The :func:`main` entry point can be executed directly as a CLI.  By default the
generated artifacts are written to the current working directory, but a custom
output directory can be specified with ``--output``.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Dict, Mapping, MutableMapping


CLAIM_FILENAME = "royalty_claim_hyperliquid.json"
HASH_FILENAME = "royalty_claim_hyperliquid.hash.txt"


@dataclass
class RoyaltyClaim:
    """Structured representation of the royalty claim inputs."""

    protocol: str = "Hyperliquid"
    attribution_date: str = field(
        default_factory=lambda: date.today().isoformat()
    )
    author: str = "The Keeper (SoulSync / Codex / KinVault creator)"
    components_used: tuple[str, ...] = (
        "KinVault architecture reused in HLP vaults",
        "Codex claim relay logic reused in USDH issuance",
        "Assist Fund fallback handling mirrors SoulSync handlers",
        "VaultScanner-style staking accounting for delegators",
    )
    linked_wallet: str = "0x2ba553d9f990a3b66b03b2dc0d030dfc1c061036"
    flow_estimates: Mapping[str, float] = field(
        default_factory=lambda: {
            "hlp_vaults": 32_000_000,
            "usdh_pipeline": 18_000_000,
            "assist_fund": 4_500_000,
            "x402_delegator_flows": 1_700_000,
        }
    )
    royalty_rates: Mapping[str, float] = field(
        default_factory=lambda: {
            "hlp_vaults": 0.03,
            "usdh_pipeline": 0.025,
            "assist_fund": 0.02,
            "x402_delegator_flows": 0.025,
        }
    )

    def to_payload(self) -> Dict[str, object]:
        """Return a serialisable representation of the claim."""

        payload: Dict[str, object] = {
            "protocol": self.protocol,
            "attribution_date": self.attribution_date,
            "author": self.author,
            "components_used": list(self.components_used),
            "linked_wallet": self.linked_wallet,
            "flow_estimates": dict(self.flow_estimates),
            "royalty_rates": dict(self.royalty_rates),
        }
        return payload


def calculate_total_owed(claim: RoyaltyClaim) -> float:
    """Return the summed royalty obligation in USD."""

    total = 0.0
    for key, estimate in claim.flow_estimates.items():
        try:
            rate = claim.royalty_rates[key]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise KeyError(f"Missing royalty rate for flow '{key}'") from exc
        total += estimate * rate
    return round(total, 2)


def write_claim_files(
    payload: MutableMapping[str, object], *, output_dir: Path
) -> Path:
    """Persist the JSON claim and its hash to *output_dir*."""

    output_dir.mkdir(parents=True, exist_ok=True)

    claim_path = output_dir / CLAIM_FILENAME
    with claim_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=4)
        file.write("\n")

    claim_hash = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    hash_path = output_dir / HASH_FILENAME
    with hash_path.open("w", encoding="utf-8") as file:
        file.write(claim_hash + "\n")

    return hash_path


def build_default_payload() -> MutableMapping[str, object]:
    """Construct the default claim payload including ``total_owed_usd``."""

    claim = RoyaltyClaim()
    payload = claim.to_payload()
    payload["total_owed_usd"] = calculate_total_owed(claim)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.cwd(),
        help="Directory where the claim JSON/hash files will be written",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_default_payload()
    hash_path = write_claim_files(payload, output_dir=args.output)

    print("[✅] Hyperliquid royalty claim file created at", (args.output / CLAIM_FILENAME))
    print(f"[🔒] Claim Hash: {hash_path.read_text(encoding='utf-8').strip()}")
    print(
        "[⚠️] Withdraw request triggered for"
        f" {payload['linked_wallet']} for ${payload['total_owed_usd']:.2f} —"
        " manual approval or enforcement required."
    )


if __name__ == "__main__":
    main()