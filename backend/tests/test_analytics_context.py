from datetime import datetime, timedelta

from backend.services.analytics_context import build_financial_context


def _recent_date(days_ago: int) -> str:
    return (
        datetime.now() - timedelta(days=days_ago)
    ).isoformat()


def _tx(days_ago, amount, tx_type, category="Food"):
    return {
        "date": _recent_date(days_ago),
        "amount": amount,
        "type": tx_type,
        "category": category,
        "merchant": "M",
    }


def test_build_financial_context_combines_health_and_anomalies():
    transactions = [
        _tx(d, -100, "expense")
        for d in range(1, 10)
    ]

    transactions.append(
        _tx(
            10,
            -5000,
            "expense",
        )
    )

    transactions.append(
        _tx(
            11,
            5000,
            "income",
            category="salary",
        )
    )

    ctx = build_financial_context(
        transactions
    )

    assert ctx.transaction_summary.total_expense > 0
    assert "score" in ctx.health
    assert isinstance(
        ctx.top_anomalies,
        list,
    )
    assert len(ctx.top_anomalies) >= 1


def test_to_prompt_dict_shape_and_forecast_defaults_none():
    ctx = build_financial_context([])

    payload = ctx.to_prompt_dict()

    assert set(payload.keys()) == {
        "transaction_summary",
        "financial_health",
        "flagged_anomalies",
        "latest_forecast",
    }

    assert payload["latest_forecast"] is None