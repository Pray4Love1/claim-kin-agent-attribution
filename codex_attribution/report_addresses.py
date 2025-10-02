"""Utilities for extracting contract addresses from Codex proof bundles."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable, List, Sequence


def _unique(iterable: Iterable[str]) -> List[str]:
    seen: dict[str, None] = {}
    order: List[str] = []
    for item in iterable:
        key = item.lower()
        if key in seen:
            continue
        seen[key] = None
        order.append(item)
    return order


def _extract_addresses_from_csv(csv_path: Path) -> Sequence[str]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        fieldnames = rows.fieldnames or []
        address_fields = [name for name in fieldnames if name and "address" in name.lower()]
        if not address_fields:
            return []

        addresses: list[str] = []
        for row in rows:
            for field in address_fields:
                value = row.get(field) or ""
                value = value.strip()
                if value and value.startswith("0x") and len(value) >= 4:
                    addresses.append(value)
        return addresses


def extract_addresses(report_path: Path) -> List[str]:
    """Return the unique contract addresses referenced by a proof report."""

    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    bundle: Sequence[str] = report_data.get("proof_bundle", [])  # type: ignore[assignment]
    base_dir = report_path.parent

    addresses: list[str] = []
    for entry in bundle:
        entry_path = base_dir / entry
        if entry_path.suffix.lower() != ".csv" or not entry_path.exists():
            continue
        addresses.extend(_extract_addresses_from_csv(entry_path))

    return _unique(addresses)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Extract contract addresses from a Codex proof bundle report.")
    parser.add_argument("report", type=Path, help="Path to proof_overlap_report.json")
    args = parser.parse_args(argv)

    addresses = extract_addresses(args.report)
    for address in addresses:
        print(address)


if __name__ == "__main__":
    main()
