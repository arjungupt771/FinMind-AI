from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.forecasting.forecasting import (
    FinancialForecaster,
)
from backend.forecasting.evaluation import (
    compute_metrics,
    naive_forecast,
    seasonal_naive_forecast,
    select_best_model,
    walk_forward_validate,
)


def make_transactions(days=120):
    transactions = []

    start = datetime(2026, 1, 1)

    for index in range(days):
        date = start + timedelta(days=index)

        transactions.append(
            {
                "date": date.isoformat(),
                "merchant": "Test Store",
                "amount": -(
                    100 + (index % 7) * 10
                ),
                "type": "expense",
                "category": "Food",
            }
        )

    return transactions


def test_daily_time_series():
    transactions = make_transactions()

    df = FinancialForecaster.prepare_time_series(
        transactions,
        "expense",
    )

    assert not df.empty
    assert list(df.columns) == [
        "ds",
        "y",
    ]
    assert len(df) == 120


def test_monthly_time_series():
    transactions = make_transactions(
        days=180
    )

    df = FinancialForecaster.prepare_monthly_data(
        transactions,
        "expense",
    )

    assert not df.empty
    assert len(df) >= 5


def test_naive_forecast():
    df = pd.DataFrame(
        {
            "ds": pd.date_range(
                "2026-01-01",
                periods=10,
            ),
            "y": np.arange(10),
        }
    )

    result = naive_forecast(
        df,
        3,
    )

    assert len(result) == 3
    assert np.all(
        result == 9
    )


def test_seasonal_naive():
    df = pd.DataFrame(
        {
            "ds": pd.date_range(
                "2026-01-01",
                periods=14,
            ),
            "y": np.arange(14),
        }
    )

    result = seasonal_naive_forecast(
        7
    )(
        df,
        3,
    )

    assert len(result) == 3
    assert result[0] == 7


def test_metrics():
    y_true = np.array(
        [100, 200, 300]
    )

    y_pred = np.array(
        [110, 190, 310]
    )

    metrics = compute_metrics(
        y_true,
        y_pred,
    )

    assert metrics["mae"] > 0
    assert metrics["rmse"] > 0
    assert metrics["mape"] is not None
    assert metrics["smape"] > 0


def test_walk_forward_validation():
    df = pd.DataFrame(
        {
            "ds": pd.date_range(
                "2026-01-01",
                periods=40,
            ),
            "y": np.arange(40)
            + 100,
        }
    )

    folds = walk_forward_validate(
        df,
        naive_forecast,
        horizon=3,
        min_train_size=14,
        step=3,
    )

    assert len(folds) > 0

    for fold in folds:
        assert "mae" in fold
        assert "rmse" in fold
        assert "smape" in fold


def test_model_selection():
    evaluation = {
        "naive": {
            "folds_evaluated": 5,
            "mae": 20,
            "rmse": 25,
            "mape": 15,
            "smape": 18,
        },
        "prophet": {
            "folds_evaluated": 5,
            "mae": 10,
            "rmse": 15,
            "mape": 8,
            "smape": 9,
        },
    }

    result = select_best_model(
        evaluation
    )

    assert result["model"] == "prophet"
    assert result["criterion"] == "smape"