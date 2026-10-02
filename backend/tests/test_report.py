import pytest

from backend.forecasting.report import generate_forecast_evaluation_report


@pytest.mark.asyncio
async def test_monthly_granularity_uses_fewer_required_points():
    from datetime import datetime, timedelta

    start = datetime(2026, 1, 1)

    transactions = [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "amount": -100 - (i % 10),
            "category": "Food",
            "merchant": "M",
        }
        for i in range(240)
    ]

    report = await generate_forecast_evaluation_report(
        transactions,
        metric_type="expense",
        horizon=1,
        min_train_size=6,
        granularity="monthly",
    )

    assert "error" not in report
    assert report["granularity"] == "monthly"
    assert report["best_model"] is not None