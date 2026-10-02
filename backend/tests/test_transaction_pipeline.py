from datetime import datetime

import pytest

from backend.services.transaction_pipeline import (
    CanonicalTransaction,
    normalize_transaction,
)


def test_normalizes_expense():
    tx = normalize_transaction(
        {
            "date": "2026-10-01T10:30:00",
            "merchant": "  Swiggy  ",
            "amount": "1,250",
            "type": "EXPENSE",
            "category": " Food ",
            "source": " CSV ",
        }
    )

    assert tx.merchant == "Swiggy"
    assert tx.amount == 1250.0
    assert tx.transaction_type == "expense"
    assert tx.category == "Food"
    assert tx.source == "csv"
    assert tx.signed_amount == -1250.0


def test_normalizes_income():
    tx = normalize_transaction(
        {
            "date": "2026-10-01",
            "merchant": "Company",
            "amount": "50000",
            "type": "credit",
            "category": "Salary",
        }
    )

    assert tx.amount == 50000.0
    assert tx.transaction_type == "income"
    assert tx.signed_amount == 50000.0


def test_negative_amount_becomes_positive_storage_amount():
    tx = normalize_transaction(
        {
            "date": "2026-10-01",
            "merchant": "Amazon",
            "amount": -999,
            "type": "expense",
        }
    )

    assert tx.amount == 999.0
    assert tx.signed_amount == -999.0


def test_currency_symbols_are_removed():
    tx = normalize_transaction(
        {
            "date": "2026-10-01",
            "merchant": "Restaurant",
            "amount": "₹1,499.50",
            "type": "expense",
        }
    )

    assert tx.amount == 1499.50


def test_missing_category_defaults_to_other():
    tx = normalize_transaction(
        {
            "date": "2026-10-01",
            "merchant": "Unknown Store",
            "amount": 500,
            "type": "expense",
        }
    )

    assert tx.category == "Other"


def test_missing_source_defaults_to_manual():
    tx = normalize_transaction(
        {
            "date": "2026-10-01",
            "merchant": "Store",
            "amount": 500,
            "type": "expense",
        }
    )

    assert tx.source == "manual"


def test_invalid_transaction_type_is_rejected():
    with pytest.raises(ValueError, match="transaction_type"):
        normalize_transaction(
            {
                "date": "2026-10-01",
                "merchant": "Store",
                "amount": 500,
                "type": "random",
            }
        )


def test_zero_amount_is_rejected():
    with pytest.raises(ValueError, match="greater than zero"):
        normalize_transaction(
            {
                "date": "2026-10-01",
                "merchant": "Store",
                "amount": 0,
                "type": "expense",
            }
        )


def test_missing_merchant_is_rejected():
    with pytest.raises(ValueError, match="merchant"):
        normalize_transaction(
            {
                "date": "2026-10-01",
                "amount": 500,
                "type": "expense",
            }
        )


def test_storage_representation_matches_existing_database_contract():
    tx = normalize_transaction(
        {
            "date": "2026-10-01T10:30:00",
            "merchant": "Amazon",
            "amount": -1200,
            "type": "expense",
            "category": "Shopping",
            "source": "csv",
        }
    )

    storage = tx.to_storage_dict()

    assert storage["amount"] == 1200.0
    assert storage["transaction_type"] == "expense"
    assert storage["category"] == "Shopping"
    assert storage["source"] == "csv"


def test_analytics_representation_uses_signed_amount():
    tx = CanonicalTransaction(
        date=datetime(2026, 10, 1),
        merchant="Salary",
        amount=50000,
        transaction_type="income",
        category="Salary",
        source="bank",
    )

    analytics = tx.to_analytics_dict()

    assert analytics["amount"] == 50000
    assert analytics["type"] == "income"
    assert analytics["transaction_type"] == "income"