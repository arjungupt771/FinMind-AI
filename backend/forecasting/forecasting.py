"""
Financial forecasting engine.

Phase 7:
- Daily and monthly forecasting
- Naive baseline
- Seasonal naive
- Moving average
- Exponential smoothing
- Prophet
- XGBoost
- Model selection
- Confidence intervals
- Stable horizon semantics
"""

import logging

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from backend.utils.datetime import utcnow


try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False


try:
    import xgboost as xgb

    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False


logger = logging.getLogger(__name__)


HORIZON_MAP = {
    "1m": 1,
    "3m": 3,
    "6m": 6,
    "12m": 12,
}


class FinancialForecaster:
    """Forecast financial metrics."""

    def __init__(self):
        self.prophet_available = PROPHET_AVAILABLE
        self.xgboost_available = XGBOOST_AVAILABLE

    # ================================================================
    # DATA PREPARATION
    # ================================================================

    @staticmethod
    def _transaction_type(tx: Dict[str, Any]) -> str:
        value = str(
            tx.get(
                "transaction_type",
                tx.get("type", ""),
            )
        ).lower()

        return value

    @staticmethod
    def _amount(tx: Dict[str, Any]) -> float:
        return float(tx.get("amount", 0) or 0)

    @staticmethod
    def prepare_time_series(
        transactions: List[Dict[str, Any]],
        metric_type: str = "expense",
    ) -> pd.DataFrame:
        """
        Prepare DAILY time series.
        """

        daily_data = defaultdict(float)

        for tx in transactions:
            try:
                raw_date = tx.get("date")

                if isinstance(raw_date, datetime):
                    tx_date = raw_date
                else:
                    tx_date = datetime.fromisoformat(
                        str(raw_date).replace(
                            "Z",
                            "+00:00",
                        )
                    )

                tx_date = tx_date.replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                    tzinfo=None,
                )

                amount = FinancialForecaster._amount(tx)
                tx_type = FinancialForecaster._transaction_type(tx)

                is_income = (
                    tx_type == "income"
                    or amount > 0
                )

                if metric_type == "expense":
                    if not is_income:
                        daily_data[tx_date] += abs(amount)

                elif metric_type == "income":
                    if is_income:
                        daily_data[tx_date] += abs(amount)

                elif metric_type == "savings":
                    if is_income:
                        daily_data[tx_date] += abs(amount)
                    else:
                        daily_data[tx_date] -= abs(amount)

            except Exception:
                continue

        if not daily_data:
            return pd.DataFrame(
                columns=["ds", "y"]
            )

        df = pd.DataFrame(
            [
                {
                    "ds": date,
                    "y": value,
                }
                for date, value
                in sorted(daily_data.items())
            ]
        )

        df["ds"] = pd.to_datetime(df["ds"])

        df = (
            df.set_index("ds")
            .resample("D")
            .sum()
            .fillna(0)
            .reset_index()
        )

        return df[["ds", "y"]]

    @staticmethod
    def prepare_monthly_data(
        transactions: List[Dict[str, Any]],
        metric_type: str = "expense",
    ) -> pd.DataFrame:
        """
        Prepare MONTHLY time series.
        """

        daily = FinancialForecaster.prepare_time_series(
            transactions,
            metric_type,
        )

        if daily.empty:
            return pd.DataFrame(
                columns=["ds", "y"]
            )

        daily["ds"] = pd.to_datetime(
            daily["ds"]
        )

        monthly = (
            daily.set_index("ds")
            .resample("MS")
            .sum()
            .reset_index()
        )

        return monthly[["ds", "y"]]

    # ================================================================
    # PROPHET
    # ================================================================

    def forecast_with_prophet(
        self,
        df: pd.DataFrame,
        periods: int = 30,
        interval_width: float = 0.95,
        frequency: str = "D",
    ) -> Optional[Dict[str, Any]]:

        if not self.prophet_available:
            return None

        if df.empty or len(df) < 14:
            return None

        try:
            model = Prophet(
                yearly_seasonality=(
                    len(df) >= 60
                    if frequency == "D"
                    else len(df) >= 12
                ),
                weekly_seasonality=(
                    frequency == "D"
                    and len(df) >= 14
                ),
                daily_seasonality=False,
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10,
                interval_width=interval_width,
            )

            model.fit(
                df[["ds", "y"]]
            )

            future = model.make_future_dataframe(
                periods=periods,
                freq=frequency,
            )

            forecast = model.predict(
                future
            )

            result = forecast[
                forecast["ds"] > df["ds"].max()
            ][
                [
                    "ds",
                    "yhat",
                    "yhat_lower",
                    "yhat_upper",
                ]
            ].head(periods)

            return {
                "method": "prophet",
                "forecast": result.to_dict(
                    "records"
                ),
                "model_params": {
                    "periods": periods,
                    "frequency": frequency,
                    "interval_width": interval_width,
                },
            }

        except Exception as exc:
            logger.warning(
                "Prophet forecasting failed: %s",
                exc,
            )
            return None

    # ================================================================
    # XGBOOST
    # ================================================================

    def forecast_with_xgboost(
        self,
        df: pd.DataFrame,
        periods: int = 30,
        frequency: str = "D",
    ) -> Optional[Dict[str, Any]]:

        if not self.xgboost_available:
            return None

        try:
            if df.empty:
                return None

            data = df.copy()

            data["date"] = pd.to_datetime(
                data["ds"]
            )

            data["month"] = (
                data["date"].dt.month
            )

            data["quarter"] = (
                data["date"].dt.quarter
            )

            data["day_of_year"] = (
                data["date"].dt.dayofyear
            )

            data["day_of_week"] = (
                data["date"].dt.dayofweek
            )

            data["lag_1"] = data["y"].shift(1)

            lag_2 = (
                7 if frequency == "D"
                else 3
            )

            lag_3 = (
                30 if frequency == "D"
                else 6
            )

            data["lag_2"] = data["y"].shift(
                lag_2
            )

            data["lag_3"] = data["y"].shift(
                lag_3
            )

            rolling_short = (
                7 if frequency == "D"
                else 3
            )

            rolling_long = (
                30 if frequency == "D"
                else 6
            )

            data["rolling_short"] = (
                data["y"]
                .rolling(rolling_short)
                .mean()
            )

            data["rolling_long"] = (
                data["y"]
                .rolling(rolling_long)
                .mean()
            )

            data = data.dropna()

            if len(data) < 12:
                return None

            feature_cols = [
                "month",
                "quarter",
                "day_of_year",
                "day_of_week",
                "lag_1",
                "lag_2",
                "lag_3",
                "rolling_short",
                "rolling_long",
            ]

            model = xgb.XGBRegressor(
                n_estimators=200,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                objective="reg:squarederror",
                random_state=42,
            )

            model.fit(
                data[feature_cols],
                data["y"],
            )

            history = list(
                df["y"].astype(float)
            )

            last_date = pd.Timestamp(
                df["ds"].max()
            )

            forecast = []

            step = (
                timedelta(days=1)
                if frequency == "D"
                else None
            )

            for _ in range(periods):

                if frequency == "D":
                    next_date = (
                        last_date + step
                    )
                else:
                    next_date = (
                        last_date
                        + pd.offsets.MonthBegin(1)
                    )

                lag1 = (
                    history[-1]
                )

                lag2 = (
                    history[-lag_2]
                    if len(history) >= lag_2
                    else history[-1]
                )

                lag3 = (
                    history[-lag_3]
                    if len(history) >= lag_3
                    else history[-1]
                )

                short_values = history[
                    -rolling_short:
                ]

                long_values = history[
                    -rolling_long:
                ]

                features = pd.DataFrame(
                    [{
                        "month": next_date.month,
                        "quarter": (
                            (next_date.month - 1)
                            // 3
                            + 1
                        ),
                        "day_of_year": (
                            next_date.dayofyear
                        ),
                        "day_of_week": (
                            next_date.dayofweek
                        ),
                        "lag_1": lag1,
                        "lag_2": lag2,
                        "lag_3": lag3,
                        "rolling_short": (
                            np.mean(short_values)
                        ),
                        "rolling_long": (
                            np.mean(long_values)
                        ),
                    }]
                )

                prediction = float(
                    model.predict(
                        features
                    )[0]
                )

                prediction = max(
                    0.0,
                    prediction,
                )

                forecast.append(
                    {
                        "ds": next_date,
                        "yhat": prediction,
                        "yhat_lower": prediction * 0.8,
                        "yhat_upper": prediction * 1.2,
                    }
                )

                history.append(
                    prediction
                )

                last_date = pd.Timestamp(
                    next_date
                )

            return {
                "method": "xgboost",
                "forecast": forecast,
                "model_params": {
                    "periods": periods,
                    "frequency": frequency,
                },
            }

        except Exception as exc:
            logger.warning(
                "XGBoost forecasting failed: %s",
                exc,
            )
            return None

    # ================================================================
    # EXPONENTIAL SMOOTHING
    # ================================================================

    def simple_exponential_smoothing(
        self,
        df: pd.DataFrame,
        periods: int = 30,
        alpha: float = 0.3,
        frequency: str = "D",
    ) -> Optional[Dict[str, Any]]:

        if df.empty or len(df) < 3:
            return None

        try:
            values = (
                df["y"]
                .astype(float)
                .tolist()
            )

            smoothed = values[0]

            for value in values[1:]:
                smoothed = (
                    alpha * value
                    + (1 - alpha) * smoothed
                )

            forecast = []

            last_date = pd.Timestamp(
                df["ds"].max()
            )

            for index in range(periods):

                if frequency == "D":
                    next_date = (
                        last_date
                        + timedelta(days=index + 1)
                    )
                else:
                    next_date = (
                        last_date
                        + pd.offsets.MonthBegin(
                            index + 1
                        )
                    )

                uncertainty = (
                    0.15
                    + 0.02 * index
                )

                forecast.append(
                    {
                        "ds": next_date,
                        "yhat": max(
                            0.0,
                            smoothed,
                        ),
                        "yhat_lower": max(
                            0.0,
                            smoothed
                            * (1 - uncertainty),
                        ),
                        "yhat_upper": max(
                            0.0,
                            smoothed
                            * (1 + uncertainty),
                        ),
                    }
                )

            return {
                "method": "exponential_smoothing",
                "forecast": forecast,
                "model_params": {
                    "alpha": alpha,
                    "periods": periods,
                    "frequency": frequency,
                },
            }

        except Exception as exc:
            logger.warning(
                "Exponential smoothing failed: %s",
                exc,
            )
            return None

    # ================================================================
    # UNIFIED FORECAST
    # ================================================================

    def forecast(
        self,
        transactions: List[Dict[str, Any]],
        metric_type: str = "expense",
        horizon: str = "1m",
        frequency: str = "M",
        method: Optional[str] = None,
    ) -> Dict[str, Any]:

        if horizon not in HORIZON_MAP:
            raise ValueError(
                "horizon must be one of "
                "1m, 3m, 6m, 12m"
            )

        if frequency not in {"D", "M"}:
            raise ValueError(
                "frequency must be D or M"
            )

        if frequency == "D":
            periods = {
                "1m": 30,
                "3m": 90,
                "6m": 180,
                "12m": 365,
            }[horizon]

            df = self.prepare_time_series(
                transactions,
                metric_type,
            )

        else:
            periods = HORIZON_MAP[horizon]

            df = self.prepare_monthly_data(
                transactions,
                metric_type,
            )

        if df.empty:
            return {
                "forecast_type": metric_type,
                "horizon": horizon,
                "frequency": frequency,
                "method": "none",
                "forecast": [],
                "error": "Insufficient transaction data",
            }

        candidates = []

        if method in (None, "prophet"):
            if self.prophet_available:
                candidates.append(
                    (
                        "prophet",
                        lambda: self.forecast_with_prophet(
                            df,
                            periods=periods,
                            frequency=frequency,
                        ),
                    )
                )

        if method in (None, "xgboost"):
            if self.xgboost_available:
                candidates.append(
                    (
                        "xgboost",
                        lambda: self.forecast_with_xgboost(
                            df,
                            periods=periods,
                            frequency=frequency,
                        ),
                    )
                )

        if method in (
            None,
            "exponential_smoothing",
        ):
            candidates.append(
                (
                    "exponential_smoothing",
                    lambda: self.simple_exponential_smoothing(
                        df,
                        periods=periods,
                        frequency=frequency,
                    ),
                )
            )

        selected = None

        for name, generator in candidates:
            result = generator()

            if result:
                selected = result
                break

        if not selected:
            return {
                "forecast_type": metric_type,
                "horizon": horizon,
                "frequency": frequency,
                "method": "none",
                "forecast": [],
                "error": "No forecasting model available",
            }

        forecast_values = selected.get(
            "forecast",
            [],
        )

        return {
            "forecast_type": metric_type,
            "horizon": horizon,
            "frequency": frequency,
            "method": selected["method"],
            "forecast": forecast_values,
            "periods": periods,
            "historical_points": len(df),
            "timestamp": utcnow().isoformat(),
        }


# ====================================================================
# Backward-compatible public functions
# ====================================================================

async def forecast_expense(
    transactions: List[Dict[str, Any]],
    horizon: str = "1m",
    user_id: str = None,
) -> Dict[str, Any]:

    result = FinancialForecaster().forecast(
        transactions=transactions,
        metric_type="expense",
        horizon=horizon,
        frequency="M",
    )

    result["user_id"] = user_id

    return result


async def forecast_savings(
    transactions: List[Dict[str, Any]],
    horizon: str = "1m",
    user_id: str = None,
) -> Dict[str, Any]:

    result = FinancialForecaster().forecast(
        transactions=transactions,
        metric_type="savings",
        horizon=horizon,
        frequency="M",
    )

    result["user_id"] = user_id

    return result


async def forecast_income(
    transactions: List[Dict[str, Any]],
    horizon: str = "1m",
    user_id: str = None,
) -> Dict[str, Any]:

    result = FinancialForecaster().forecast(
        transactions=transactions,
        metric_type="income",
        horizon=horizon,
        frequency="M",
    )

    result["user_id"] = user_id

    return result