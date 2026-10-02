from backend.services.transaction_csv import (
    detect_columns,
    parse_csv_transactions,
)


def test_detect_columns():
    headers = [
        "Transaction Date",
        "Merchant",
        "Amount",
        "Type",
        "Category",
    ]

    mapping = detect_columns(headers)

    assert mapping["date"] == "Transaction Date"
    assert mapping["merchant"] == "Merchant"
    assert mapping["amount"] == "Amount"
    assert mapping["type"] == "Type"
    assert mapping["category"] == "Category"


def test_parse_csv_transactions():
    csv_content = b"""Date,Merchant,Amount,Type,Category
2026-09-01,Amazon,1200,expense,Shopping
2026-09-02,Salary,50000,income,Salary
"""

    rows, errors = parse_csv_transactions(csv_content)

    assert len(rows) == 2
    assert errors == []

    assert rows[0]["merchant"] == "Amazon"
    assert rows[0]["amount"] == "1200"
    assert rows[0]["type"] == "expense"
    assert rows[0]["category"] == "Shopping"

    assert rows[1]["merchant"] == "Salary"
    assert rows[1]["type"] == "income"


def test_parse_csv_defaults():
    csv_content = b"""Date,Merchant,Amount
2026-09-01,Amazon,1200
"""

    rows, errors = parse_csv_transactions(csv_content)

    assert errors == []
    assert len(rows) == 1

    assert rows[0]["type"] == "expense"
    assert rows[0]["category"] == "Other"
    assert rows[0]["source"] == "csv"


def test_parse_csv_missing_required_column():
    csv_content = b"""Date,Merchant,Category
2026-09-01,Amazon,Shopping
"""

    try:
        parse_csv_transactions(csv_content)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "amount" in str(exc).lower()

def test_parse_debit_credit_csv():
    csv_content = b"""Date,Description,Debit,Credit
2026-09-01,Amazon,1200,
2026-09-02,Salary,,50000
"""

    rows, errors = parse_csv_transactions(csv_content)

    assert errors == []
    assert len(rows) == 2

    assert rows[0]["merchant"] == "Amazon"
    assert rows[0]["amount"] == "1200"
    assert rows[0]["type"] == "expense"

    assert rows[1]["merchant"] == "Salary"
    assert rows[1]["amount"] == "50000"
    assert rows[1]["type"] == "income"


def test_parse_debit_credit_with_currency():
    csv_content = """Date,Description,Debit,Credit
    2026-09-01,Amazon,"₹1,200",
    2026-09-02,Salary,,"₹50,000"
"""

    rows, errors = parse_csv_transactions(csv_content)

    assert errors == []
    assert len(rows) == 2

    assert rows[0]["amount"] == "1200"
    assert rows[0]["type"] == "expense"

    assert rows[1]["amount"] == "50000"
    assert rows[1]["type"] == "income"


def test_parse_signed_amount_csv():
    csv_content = b"""Date,Description,Amount
2026-09-01,Amazon,-1200
2026-09-02,Salary,50000
"""

    rows, errors = parse_csv_transactions(csv_content)

    assert errors == []
    assert len(rows) == 2

    assert rows[0]["amount"] == "1200"
    assert rows[0]["type"] == "expense"

    assert rows[1]["amount"] == "50000"
    assert rows[1]["type"] == "income"


def test_reject_both_debit_and_credit():
    csv_content = b"""Date,Description,Debit,Credit
2026-09-01,Invalid,100,200
"""

    rows, errors = parse_csv_transactions(csv_content)

    assert len(rows) == 0
    assert len(errors) == 1
    assert errors[0]["row"] == 2
    assert "both debit and credit" in errors[0]["error"].lower()


def test_reject_empty_debit_and_credit():
    csv_content = b"""Date,Description,Debit,Credit
2026-09-01,Invalid,,
"""

    rows, errors = parse_csv_transactions(csv_content)

    assert len(rows) == 0
    assert len(errors) == 1
    assert "neither debit nor credit" in errors[0]["error"].lower()