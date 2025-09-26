"""Compatibility package exposing attribution and settlement helpers."""
from __future__ import annotations

from .builder_codes import BuilderCode, fetch_builder_codes, filter_builder_codes, parse_builder_codes
from .github_helpers import (
    CommitAuthor,
    GitHubSourceControlHistoryItemDetailsProvider,
    _extract_commit_author_details,
    _normalise_repo,
)
from .payments import PaymentSettlement, extract_payment_settlements, total_settlement_amount

__all__ = [
    "BuilderCode",
    "CommitAuthor",
    "GitHubSourceControlHistoryItemDetailsProvider",
    "fetch_builder_codes",
    "filter_builder_codes",
    "PaymentSettlement",
    "parse_builder_codes",
    "_extract_commit_author_details",
    "_normalise_repo",
    "extract_payment_settlements",
    "total_settlement_amount",
]
