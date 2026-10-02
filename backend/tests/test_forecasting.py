from backend.forecasting.forecasting import FinancialForecaster


def _tx(date, amount):
    return {"date": date, "amount": amount}


def test_prepare_time_series_aggregates_expenses_per_day():
    forecaster = FinancialForecaster()
    transactions = [
        _tx("2026-01-01T00:00:00", -100),
        _tx("2026-01-01T00:00:00", -50),
        _tx("2026-01-02T00:00:00", -200),
        _tx("2026-01-02T00:00:00", 500),  # income, should be ignored for 'expense'
    ]
    df = forecaster.prepare_time_series(transactions, metric_type="expense")
    assert not df.empty
    assert df["y"].sum() == 350


def test_prepare_time_series_empty_input():
    forecaster = FinancialForecaster()
    df = forecaster.prepare_time_series([], metric_type="expense")
    assert df.empty


def test_simple_exponential_smoothing_produces_requested_periods():
    forecaster = FinancialForecaster()
    transactions = [_tx(f"2026-01-{d:02d}T00:00:00", -100 - d) for d in range(1, 15)]
    df = forecaster.prepare_time_series(transactions, metric_type="expense")

    result = forecaster.simple_exponential_smoothing(df, periods=7)
    assert result is not None
    assert result["method"] == "exponential_smoothing"
    assert len(result["forecast"]) == 7
    assert all(point["yhat"] >= 0 for point in result["forecast"])


def test_simple_exponential_smoothing_insufficient_data_returns_none():
    forecaster = FinancialForecaster()
    df = forecaster.prepare_time_series([_tx("2026-01-01T00:00:00", -10)], metric_type="expense")
    result = forecaster.simple_exponential_smoothing(df, periods=5)
    assert result is None