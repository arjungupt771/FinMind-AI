import numpy as np
import pandas as pd
import pytest

from backend.forecasting.evaluation import (
    mae, rmse, mape, smape,
    naive_forecast, moving_average_forecast, seasonal_naive_forecast,
    walk_forward_validate, compare_forecasters,
)


def _make_df(values):
    return pd.DataFrame({
        "ds": pd.date_range("2026-01-01", periods=len(values), freq="D"),
        "y": values,
    })


def test_mae_rmse_basic():
    y_true = [10, 20, 30]
    y_pred = [12, 18, 33]
    assert mae(y_true, y_pred) == pytest.approx((2 + 2 + 3) / 3)
    assert rmse(y_true, y_pred) > 0


def test_mape_ignores_zero_actuals_instead_of_exploding():
    y_true = [0, 10, 20]
    y_pred = [5, 11, 22]
    result = mape(y_true, y_pred)
    assert result is not None
    assert result < 100  # would be inflated/undefined if the zero actual weren't excluded


def test_mape_returns_none_when_all_actuals_zero():
    assert mape([0, 0, 0], [1, 2, 3]) is None


def test_smape_bounded_and_defined_at_zero():
    result = smape([0, 0], [0, 0])
    assert result == 0.0


def test_naive_forecast_repeats_last_value():
    df = _make_df([10, 20, 30])
    pred = naive_forecast(df, periods=3)
    assert list(pred) == [30, 30, 30]


def test_seasonal_naive_needs_full_season():
    df = _make_df([1, 2, 3])
    assert seasonal_naive_forecast(season_length=7)(df, periods=3) is None

    df_long = _make_df(list(range(14)))
    pred = seasonal_naive_forecast(season_length=7)(df_long, periods=7)
    assert pred is not None
    assert len(pred) == 7


def test_walk_forward_validate_produces_multiple_folds():
    df = _make_df([100 + i for i in range(60)])  # steady upward trend, easy to predict
    folds = walk_forward_validate(df, naive_forecast, horizon=7, min_train_size=14, step=7)
    assert len(folds) > 1
    for fold in folds:
        assert fold['mae'] >= 0
        assert fold['rmse'] >= 0


def test_compare_forecasters_ranks_moving_average_against_naive():
    # Noisy-but-flat series: moving average should beat naive on this kind of data
    np.random.seed(0)
    values = list(100 + np.random.normal(0, 2, 60))
    df = _make_df(values)

    candidates = {
        "naive": naive_forecast,
        "moving_average_7d": moving_average_forecast(window=7),
    }
    comparison = compare_forecasters(df, candidates, horizon=7, min_train_size=14, step=7)

    assert comparison["naive"]["folds_evaluated"] > 0
    assert comparison["moving_average_7d"]["folds_evaluated"] > 0
    assert comparison["naive"]["skill_vs_naive"] == 0  # naive vs itself
    assert "skill_vs_naive" in comparison["moving_average_7d"]