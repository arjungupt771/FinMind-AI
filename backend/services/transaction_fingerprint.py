"""
Deterministic transaction fingerprinting.

A fingerprint identifies a transaction using stable financial attributes.

The fingerprint intentionally does NOT include:
    - source
    - description

This allows the same transaction imported from multiple sources to be
recognized as a duplicate.
"""

import hashlib
import re
from datetime import datetime
from typing import Any


def _normalize_merchant(merchant: str) -> str:
    """Normalize merchant text for fingerprint comparison."""
    value = str(merchant).strip().lower()

    # Collapse repeated whitespace.
    value = re.sub(r"\s+", " ", value)

    return value


def _normalize_date(value: datetime) -> str:
    """Normalize transaction date to a stable calendar representation."""
    return value.date().isoformat()


def _normalize_amount(amount: float) -> str:
    """Normalize amount to a stable two-decimal representation."""
    return f"{abs(float(amount)):.2f}"


def build_transaction_fingerprint(
    *,
    date: datetime,
    merchant: str,
    amount: float,
    transaction_type: str,
) -> str:
    """
    Build a deterministic SHA-256 fingerprint.

    Identity fields:
        date
        merchant
        amount
        transaction_type

    Example identity:

        2026-10-01|amazon|999.00|expense
    """

    normalized_date = _normalize_date(date)
    normalized_merchant = _normalize_merchant(merchant)
    normalized_amount = _normalize_amount(amount)
    normalized_type = str(transaction_type).strip().lower()

    identity = "|".join(
        [
            normalized_date,
            normalized_merchant,
            normalized_amount,
            normalized_type,
        ]
    )

    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def build_transaction_fingerprint_from_dict(data: dict[str, Any]) -> str:
    """
    Build a fingerprint from a canonical transaction dictionary.
    """

    return build_transaction_fingerprint(
        date=data["date"],
        merchant=data["merchant"],
        amount=data["amount"],
        transaction_type=data["transaction_type"],
    )