import pytest
from backend.forecasting.report import generate_forecast_evaluation_report


def _tx(day, amount):
    return {"date": f"2026-01-{day:02d}T00:00:00", "amount": amount, "category": "Food", "merchant": "M"}


@pytest.mark.asyncio
async def test_report_flags_insufficient_history():
    transactions = [_tx(d, -50) for d in range(1, 5)]
    report = await generate_forecast_evaluation_report(transactions, metric_type="expense", horizon=7, min_train_size=14)
    assert report["error"] == "insufficient_history"


@pytest.mark.asyncio
async def test_report_picks_a_best_model_with_enough_history():
    # 45 days of steady expenses is enough to clear min_train_size(14) + horizon(7)
    # across several walk-forward folds without needing Prophet/XGBoost installed.
    transactions = []
    day = 1
    month_days = {1: 31}
    d = 1
    from datetime import datetime, timedelta
    start = datetime(2026, 1, 1)
    for i in range(45):
        current = start + timedelta(days=i)
        transactions.append({
            "date": current.isoformat(),
            "amount": -80 - (i % 5),
            "category": "Food",
            "merchant": "M",
        })

    report = await generate_forecast_evaluation_report(transactions, metric_type="expense", horizon=7, min_train_size=14)
    assert "error" not in report
    assert report["best_model"] is not None
    assert "comparison" in report
    assert "naive" in report["comparison"]