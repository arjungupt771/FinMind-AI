from datetime import datetime, timedelta

from backend.services.financial_intelligence import (
    FinancialIntelligenceEngine,
    analyze_transactions,
)


def _date(days_ago: int = 0) -> str:
    return (
        datetime.now() - timedelta(days=days_ago)
    ).isoformat()


def test_basic_income_expense_analysis():
    transactions = [
        {
            "date": _date(1),
            "merchant": "Employer",
            "amount": 50000,
            "type": "income",
            "category": "Salary",
        },
        {
            "date": _date(2),
            "merchant": "Amazon",
            "amount": -5000,
            "type": "expense",
            "category": "Shopping",
        },
        {
            "date": _date(3),
            "merchant": "Swiggy",
            "amount": -2000,
            "type": "expense",
            "category": "Food",
        },
    ]

    result = analyze_transactions(
        transactions
    )

    assert result.transaction_count == 3
    assert result.total_income == 50000
    assert result.total_expense == 7000
    assert result.net_cash_flow == 43000
    assert result.savings_rate == 86.0


def test_positive_amount_with_explicit_expense_type():
    transactions = [
        {
            "date": _date(),
            "merchant": "Amazon",
            "amount": 1200,
            "type": "expense",
            "category": "Shopping",
        }
    ]

    result = analyze_transactions(
        transactions
    )

    assert result.total_income == 0
    assert result.total_expense == 1200
    assert result.net_cash_flow == -1200


def test_transaction_type_field_is_supported():
    transactions = [
        {
            "date": _date(),
            "merchant": "Employer",
            "amount": 50000,
            "transaction_type": "income",
            "category": "Salary",
        }
    ]

    result = analyze_transactions(
        transactions
    )

    assert result.total_income == 50000
    assert result.total_expense == 0


def test_top_categories_are_ranked_by_expense():
    transactions = [
        {
            "date": _date(),
            "merchant": "A",
            "amount": -1000,
            "type": "expense",
            "category": "Food",
        },
        {
            "date": _date(),
            "merchant": "B",
            "amount": -3000,
            "type": "expense",
            "category": "Rent",
        },
        {
            "date": _date(),
            "merchant": "C",
            "amount": -2000,
            "type": "expense",
            "category": "Food",
        },
    ]

    result = analyze_transactions(
        transactions
    )

    assert result.top_categories[0].category == "Food"
    assert result.top_categories[0].amount == 3000
    assert result.top_categories[0].transaction_count == 2

    assert result.top_categories[1].category == "Rent"
    assert result.top_categories[1].amount == 3000


def test_top_merchants_are_ranked_by_expense():
    transactions = [
        {
            "date": _date(),
            "merchant": "Amazon",
            "amount": -1000,
            "type": "expense",
            "category": "Shopping",
        },
        {
            "date": _date(),
            "merchant": "Amazon",
            "amount": -2000,
            "type": "expense",
            "category": "Shopping",
        },
        {
            "date": _date(),
            "merchant": "Swiggy",
            "amount": -1500,
            "type": "expense",
            "category": "Food",
        },
    ]

    result = analyze_transactions(
        transactions
    )

    assert result.top_merchants[0].merchant == "Amazon"
    assert result.top_merchants[0].amount == 3000
    assert result.top_merchants[0].transaction_count == 2


def test_monthly_summary():
    now = datetime.now()

    transactions = [
        {
            "date": now.replace(
                day=5,
                hour=12,
                minute=0,
                second=0,
                microsecond=0,
            ).isoformat(),
            "merchant": "Employer",
            "amount": 50000,
            "type": "income",
            "category": "Salary",
        },
        {
            "date": now.replace(
                day=10,
                hour=12,
                minute=0,
                second=0,
                microsecond=0,
            ).isoformat(),
            "merchant": "Rent",
            "amount": -15000,
            "type": "expense",
            "category": "Housing",
        },
    ]

    result = analyze_transactions(
        transactions
    )

    assert len(result.monthly_summary) == 1

    month = result.monthly_summary[0]

    assert month.income == 50000
    assert month.expense == 15000
    assert month.net_cash_flow == 35000



def test_old_transactions_are_excluded():
    transactions = [
        {
            "date": _date(5),
            "merchant": "Recent",
            "amount": -1000,
            "type": "expense",
            "category": "Food",
        },
        {
            "date": _date(60),
            "merchant": "Old",
            "amount": -100000,
            "type": "expense",
            "category": "Shopping",
        },
    ]

    result = FinancialIntelligenceEngine(
        period_days=30
    ).analyze(transactions)

    assert result.transaction_count == 2
    assert result.total_expense == 1000


def test_invalid_transactions_are_skipped():
    transactions = [
        {
            "date": "",
            "merchant": "Invalid",
            "amount": -1000,
            "type": "expense",
        },
        {
            "date": _date(),
            "merchant": "Valid",
            "amount": -500,
            "type": "expense",
            "category": "Food",
        },
    ]

    result = analyze_transactions(
        transactions
    )

    assert result.transaction_count == 1
    assert result.total_expense == 500


def test_empty_transactions():
    result = analyze_transactions([])

    assert result.transaction_count == 0
    assert result.total_income == 0
    assert result.total_expense == 0
    assert result.net_cash_flow == 0
    assert result.savings_rate == 0
    assert result.top_categories == []
    assert result.top_merchants == []


def test_investment_metrics():
    transactions = [
        {
            "date": _date(1),
            "merchant": "Employer",
            "amount": 50000,
            "type": "income",
            "category": "Salary",
        },
        {
            "date": _date(2),
            "merchant": "Mutual Fund",
            "amount": -10000,
            "type": "expense",
            "category": "Investments",
        },
        {
            "date": _date(3),
            "merchant": "Rent",
            "amount": -15000,
            "type": "expense",
            "category": "Housing",
        },
    ]

    result = analyze_transactions(transactions)

    assert result.investment_expense == 10000
    assert result.investment_ratio == 40


def test_investment_metrics_with_no_expenses():
    transactions = [
        {
            "date": _date(1),
            "merchant": "Employer",
            "amount": 50000,
            "type": "income",
            "category": "Salary",
        }
    ]

    result = analyze_transactions(transactions)

    assert result.investment_expense == 0
    assert result.investment_ratio == 0


def test_transaction_counts():
    transactions = [
        {
            "date": _date(1),
            "merchant": "Employer",
            "amount": 50000,
            "type": "income",
            "category": "Salary",
        },
        {
            "date": _date(2),
            "merchant": "Rent",
            "amount": -15000,
            "type": "expense",
            "category": "Housing",
        },
        {
            "date": _date(3),
            "merchant": "Cafe",
            "amount": -500,
            "type": "expense",
            "category": "Food",
        },
    ]

    result = analyze_transactions(transactions)

    assert result.transaction_count == 3
    assert result.income_transaction_count == 1
    assert result.expense_transaction_count == 2


def test_category_and_merchant_percentages():
    transactions = [
        {
            "date": _date(1),
            "merchant": "Employer",
            "amount": 50000,
            "type": "income",
            "category": "Salary",
        },
        {
            "date": _date(2),
            "merchant": "RentCo",
            "amount": -10000,
            "type": "expense",
            "category": "Housing",
        },
        {
            "date": _date(3),
            "merchant": "FoodCo",
            "amount": -5000,
            "type": "expense",
            "category": "Food",
        },
    ]

    result = analyze_transactions(transactions)

    housing = next(
        item
        for item in result.top_categories
        if item.category == "Housing"
    )
    rent = next(
        item
        for item in result.top_merchants
        if item.merchant == "RentCo"
    )

    assert housing.percentage == 66.67
    assert rent.percentage == 66.67