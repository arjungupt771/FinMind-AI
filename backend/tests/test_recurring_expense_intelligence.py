from datetime import datetime, timedelta

from backend.services.recurring_expense_intelligence import (
    RecurringExpenseIntelligence,
)


def make_transaction(
    date,
    merchant="Netflix",
    amount=-499,
    category="Entertainment",
):
    return {
        "date": date.isoformat(),
        "merchant": merchant,
        "amount": amount,
        "type": "expense",
        "category": category,
    }


def test_detect_monthly_recurring_expense():
    base = datetime(2026, 1, 5)

    transactions = [
        make_transaction(
            base + timedelta(days=30 * i)
        )
        for i in range(6)
    ]

    result = RecurringExpenseIntelligence().analyze(
        transactions
    )

    assert result["recurring_count"] == 1

    pattern = result["patterns"][0]

    assert pattern["cycle"] == "monthly"
    assert pattern["transaction_count"] == 6
    assert pattern["monthly_cost"] == 499
    assert pattern["annual_cost"] == 5988


def test_detect_weekly_recurring_expense():
    base = datetime(2026, 1, 5)

    transactions = [
        make_transaction(
            base + timedelta(days=7 * i),
            merchant="Gym",
            amount=-500,
            category="Fitness",
        )
        for i in range(6)
    ]

    result = RecurringExpenseIntelligence().analyze(
        transactions
    )

    assert result["recurring_count"] == 1

    pattern = result["patterns"][0]

    assert pattern["cycle"] == "weekly"
    assert pattern["monthly_cost"] > 2000


def test_income_is_ignored():
    transactions = [
        {
            "date": "2026-01-01T00:00:00",
            "merchant": "Salary",
            "amount": 100000,
            "type": "income",
            "category": "Salary",
        }
        for _ in range(6)
    ]

    result = RecurringExpenseIntelligence().analyze(
        transactions
    )

    assert result["recurring_count"] == 0


def test_insufficient_transactions():
    transactions = [
        make_transaction(
            datetime(2026, 1, 1)
        ),
        make_transaction(
            datetime(2026, 2, 1)
        ),
    ]

    result = RecurringExpenseIntelligence().analyze(
        transactions
    )

    assert result["recurring_count"] == 0


def test_price_change_detection():
    base = datetime(2026, 1, 5)

    transactions = []

    for i in range(3):
        transactions.append(
            make_transaction(
                base + timedelta(days=30 * i),
                amount=-500,
            )
        )

    for i in range(3, 6):
        transactions.append(
            make_transaction(
                base + timedelta(days=30 * i),
                amount=-650,
            )
        )

    result = RecurringExpenseIntelligence().analyze(
        transactions
    )

    pattern = result["patterns"][0]

    assert pattern["price_change_detected"] is True
    assert pattern["price_change_percentage"] > 10


def test_empty_input():
    result = RecurringExpenseIntelligence().analyze([])

    assert result["recurring_count"] == 0
    assert result["total_monthly_cost"] == 0
    assert result["patterns"] == []