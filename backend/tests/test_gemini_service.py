from datetime import datetime, timedelta

import pytest

from backend.services.gemini_service import (
    build_transaction_context,
    parse_json_response,
    AIResponse,
)


def _recent_date(days_ago: int = 1) -> str:
    return (
        datetime.now() - timedelta(days=days_ago)
    ).isoformat()


def test_build_transaction_context_empty():
    ctx = build_transaction_context([])

    assert ctx.total_income == 0
    assert ctx.recent_transactions == []


def test_build_transaction_context_computes_savings_rate():
    transactions = [
        {
            "date": _recent_date(2),
            "amount": 1000,
            "category": "Salary",
            "merchant": "Employer",
        },
        {
            "date": _recent_date(1),
            "amount": -400,
            "category": "Food",
            "merchant": "Cafe",
        },
    ]

    ctx = build_transaction_context(
        transactions,
        days=30,
    )

    assert ctx.total_income == 1000
    assert ctx.total_expense == 400
    assert ctx.savings_rate == pytest.approx(60.0)


def test_build_transaction_context_skips_bad_dates_without_crashing():
    transactions = [
        {
            "date": "",
            "amount": -100,
            "category": "Food",
        },
        {
            "date": None,
            "amount": -50,
            "category": "Travel",
        },
        {
            "date": _recent_date(1),
            "amount": -200,
            "category": "Bills",
        },
    ]

    ctx = build_transaction_context(
        transactions,
        days=30,
    )

    assert ctx.total_expense == 200


def test_parse_json_response_handles_fenced_json():
    raw = (
        '```json\n'
        '{"summary": "ok", '
        '"insights": ["a"], '
        '"recommendations": ["b"], '
        '"risk_level": "LOW"}'
        '\n```'
    )

    result = parse_json_response(raw)

    assert isinstance(result, AIResponse)
    assert result.summary == "ok"
    assert result.risk_level == "LOW"


def test_parse_json_response_falls_back_on_garbage():
    result = parse_json_response(
        "not json at all"
    )

    assert isinstance(result, AIResponse)
    assert result.risk_level == "MEDIUM"
    assert result.confidence == 0.5