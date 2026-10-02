from datetime import datetime

from backend.services.transaction_fingerprint import (
    build_transaction_fingerprint,
)


def test_same_transaction_produces_same_fingerprint():
    first = build_transaction_fingerprint(
        date=datetime(2026, 10, 1, 10, 30),
        merchant="Amazon",
        amount=999,
        transaction_type="expense",
    )

    second = build_transaction_fingerprint(
        date=datetime(2026, 10, 1, 10, 30),
        merchant="Amazon",
        amount=999,
        transaction_type="expense",
    )

    assert first == second


def test_merchant_case_does_not_change_fingerprint():
    first = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="Amazon",
        amount=999,
        transaction_type="expense",
    )

    second = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="AMAZON",
        amount=999,
        transaction_type="expense",
    )

    assert first == second


def test_merchant_whitespace_does_not_change_fingerprint():
    first = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="  Amazon   India  ",
        amount=999,
        transaction_type="expense",
    )

    second = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="Amazon India",
        amount=999,
        transaction_type="expense",
    )

    assert first == second


def test_amount_sign_does_not_change_fingerprint():
    first = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="Amazon",
        amount=999,
        transaction_type="expense",
    )

    second = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="Amazon",
        amount=-999,
        transaction_type="expense",
    )

    assert first == second


def test_different_amount_produces_different_fingerprint():
    first = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="Amazon",
        amount=999,
        transaction_type="expense",
    )

    second = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="Amazon",
        amount=1000,
        transaction_type="expense",
    )

    assert first != second


def test_different_date_produces_different_fingerprint():
    first = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="Amazon",
        amount=999,
        transaction_type="expense",
    )

    second = build_transaction_fingerprint(
        date=datetime(2026, 10, 2),
        merchant="Amazon",
        amount=999,
        transaction_type="expense",
    )

    assert first != second


def test_different_merchant_produces_different_fingerprint():
    first = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="Amazon",
        amount=999,
        transaction_type="expense",
    )

    second = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="Flipkart",
        amount=999,
        transaction_type="expense",
    )

    assert first != second


def test_different_transaction_type_produces_different_fingerprint():
    first = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="Company",
        amount=50000,
        transaction_type="income",
    )

    second = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="Company",
        amount=50000,
        transaction_type="expense",
    )

    assert first != second


def test_fingerprint_is_sha256_hex():
    fingerprint = build_transaction_fingerprint(
        date=datetime(2026, 10, 1),
        merchant="Amazon",
        amount=999,
        transaction_type="expense",
    )

    assert len(fingerprint) == 64
    assert all(char in "0123456789abcdef" for char in fingerprint)