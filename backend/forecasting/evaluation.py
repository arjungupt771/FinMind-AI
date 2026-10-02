"""
Forecast evaluation: error metrics, walk-forward validation, and baseline
comparison, so forecasting claims are backed by an actual out-of-sample
accuracy number instead of "the model ran without error."
"""
import logging
import numpy as np
import pandas as pd
from typing import Callable, Dict, List, Optional, Any

from backend.forecasting.forecasting import FinancialForecaster

logger = logging.getLogger(__name__)

ForecastFn = Callable[[pd.DataFrame, int], Optional[np.ndarray]]


# ---------------------------------------------------------------------------
# Error metrics
# ---------------------------------------------------------------------------

def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float))))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    diff = np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean(diff ** 2)))


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
    """Mean Absolute Percentage Error. Returns None if every actual value is ~0
    (common on low-spend days), since MAPE is undefined there rather than just large."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.abs(y_true) > 1e-6
    if not mask.any():
        return None
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Symmetric MAPE — bounded [0, 200], defined even when actuals hit zero,
    which is why this (not plain MAPE) is the primary metric used for ranking below."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true) + np.abs(y_pred)
    denom = np.where(denom == 0, 1e-6, denom)
    return float(np.mean(2 * np.abs(y_pred - y_true) / denom) * 100)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Optional[float]]:
    return {
        'mae': mae(y_true, y_pred),
        'rmse': rmse(y_true, y_pred),
        'mape': mape(y_true, y_pred),
        'smape': smape(y_true, y_pred),
    }


# ---------------------------------------------------------------------------
# Baseline forecasters — every candidate has the same signature:
# (train_df with 'ds'/'y' columns, periods) -> np.ndarray of length `periods`, or None
# ---------------------------------------------------------------------------

def naive_forecast(train_df: pd.DataFrame, periods: int) -> Optional[np.ndarray]:
    """Repeat the last observed value. The baseline every real model must beat."""
    y = train_df['y'].values
    if len(y) == 0:
        return None
    return np.repeat(y[-1], periods)


def moving_average_forecast(window: int = 7) -> ForecastFn:
    def _fn(train_df: pd.DataFrame, periods: int) -> Optional[np.ndarray]:
        y = train_df['y'].values
        if len(y) == 0:
            return None
        avg = np.mean(y[-window:])
        return np.repeat(avg, periods)
    return _fn


def seasonal_naive_forecast(season_length: int = 7) -> ForecastFn:
    """Repeat the value from one season back (e.g. 'same day last week'), cycling forward."""
    def _fn(train_df: pd.DataFrame, periods: int) -> Optional[np.ndarray]:
        y = train_df['y'].values
        if len(y) < season_length:
            return None
        return np.array([y[-season_length + (i % season_length)] for i in range(periods)])
    return _fn


def _extract_point_forecast(result: Optional[Dict[str, Any]], periods: int) -> Optional[np.ndarray]:
    if not result or not result.get('forecast'):
        return None
    yhats = [point['yhat'] for point in result['forecast'][:periods]]
    if len(yhats) < periods:
        return None
    return np.array(yhats, dtype=float)


def make_model_candidate(forecaster: FinancialForecaster, method: str) -> ForecastFn:
    """Wrap FinancialForecaster's dict-returning methods into the plain
    (train_df, periods) -> array signature the evaluation harness expects."""
    def _fn(train_df: pd.DataFrame, periods: int) -> Optional[np.ndarray]:
        if method == 'prophet':
            result = forecaster.forecast_with_prophet(train_df, periods=periods)
        elif method == 'xgboost':
            result = forecaster.forecast_with_xgboost(train_df, periods=periods)
        elif method == 'exponential_smoothing':
            result = forecaster.simple_exponential_smoothing(train_df, periods=periods)
        else:
            raise ValueError(f"Unknown method: {method}")
        return _extract_point_forecast(result, periods)
    return _fn


# ---------------------------------------------------------------------------
# Walk-forward validation
# ---------------------------------------------------------------------------

def walk_forward_validate(
    df: pd.DataFrame,
    forecast_fn: ForecastFn,
    horizon: int = 7,
    min_train_size: int = 14,
    step: int = 7,
) -> List[Dict[str, Any]]:
    """
    Expanding-window backtest: train on [0:k], predict the next `horizon` points,
    score against what actually happened, slide the window forward by `step`,
    repeat. This is what makes the evaluation "walk-forward" rather than a single
    lucky/unlucky train-test split.
    """
    df = df.reset_index(drop=True)
    n = len(df)
    folds = []
    train_end = min_train_size

    while train_end + horizon <= n:
        train_df = df.iloc[:train_end]
        test_df = df.iloc[train_end:train_end + horizon]
        y_true = test_df['y'].values

        try:
            y_pred = forecast_fn(train_df, horizon)
        except Exception as e:
            logger.warning(f"Forecast candidate raised on fold train_end={train_end}: {e}")
            y_pred = None

        if y_pred is None or len(y_pred) != len(y_true):
            train_end += step
            continue

        fold_metrics = compute_metrics(y_true, y_pred)
        folds.append({
            'train_size': train_end,
            'horizon': horizon,
            **fold_metrics,
        })
        train_end += step

    return folds


def compare_forecasters(
    df: pd.DataFrame,
    candidates: Dict[str, ForecastFn],
    horizon: int = 7,
    min_train_size: int = 14,
    step: int = 7,
) -> Dict[str, Any]:
    """
    Run walk-forward validation for every candidate on the SAME folds and
    aggregate. Requires a 'naive' candidate in `candidates` to compute a skill
    score (how much better than "just repeat the last value" each model is).
    """
    summary: Dict[str, Any] = {}

    for name, fn in candidates.items():
        folds = walk_forward_validate(df, fn, horizon=horizon, min_train_size=min_train_size, step=step)
        if not folds:
            summary[name] = {
                'folds_evaluated': 0, 'mae': None, 'rmse': None, 'mape': None, 'smape': None,
            }
            continue

        mape_values = [f['mape'] for f in folds if f['mape'] is not None]
        summary[name] = {
            'folds_evaluated': len(folds),
            'mae': float(np.mean([f['mae'] for f in folds])),
            'rmse': float(np.mean([f['rmse'] for f in folds])),
            'mape': float(np.mean(mape_values)) if mape_values else None,
            'smape': float(np.mean([f['smape'] for f in folds])),
        }

    naive_mae = summary.get('naive', {}).get('mae')
    for name, stats in summary.items():
        if stats['mae'] is not None and naive_mae:
            # positive = better than naive, negative = worse than just repeating the last value
            stats['skill_vs_naive'] = round(1 - (stats['mae'] / naive_mae), 4)
        else:
            stats['skill_vs_naive'] = None

    return summary


def default_candidates(forecaster: Optional[FinancialForecaster] = None) -> Dict[str, ForecastFn]:
    """The standard candidate set: baselines + whichever real models are installed."""
    forecaster = forecaster or FinancialForecaster()
    candidates: Dict[str, ForecastFn] = {
        'naive': naive_forecast,
        'seasonal_naive_7d': seasonal_naive_forecast(season_length=7),
        'moving_average_7d': moving_average_forecast(window=7),
        'exponential_smoothing': make_model_candidate(forecaster, 'exponential_smoothing'),
    }
    if forecaster.prophet_available:
        candidates['prophet'] = make_model_candidate(forecaster, 'prophet')
    if forecaster.xgboost_available:
        candidates['xgboost'] = make_model_candidate(forecaster, 'xgboost')
    return candidates

# ============================================================================
# PHASE 7 - MODEL SELECTION
# ============================================================================


def select_best_model(
    evaluation: Dict[str, Any],
    preferred_fallback: str = "naive",
) -> Dict[str, Any]:
    """
    Select the best model using out-of-sample SMAPE.

    SMAPE is used because it remains meaningful when actual values
    can approach zero.

    Falls back to MAE if SMAPE is unavailable.
    """

    valid = {
        name: stats
        for name, stats in evaluation.items()
        if stats.get("folds_evaluated", 0) > 0
    }

    if not valid:
        return {
            "model": preferred_fallback,
            "reason": "No model produced valid evaluation folds",
        }

    smape_candidates = {
        name: stats
        for name, stats in valid.items()
        if stats.get("smape") is not None
    }

    if smape_candidates:
        best_name = min(
            smape_candidates,
            key=lambda name: smape_candidates[name]["smape"],
        )

        return {
            "model": best_name,
            "criterion": "smape",
            "score": smape_candidates[best_name]["smape"],
        }

    mae_candidates = {
        name: stats
        for name, stats in valid.items()
        if stats.get("mae") is not None
    }

    if mae_candidates:
        best_name = min(
            mae_candidates,
            key=lambda name: mae_candidates[name]["mae"],
        )

        return {
            "model": best_name,
            "criterion": "mae",
            "score": mae_candidates[best_name]["mae"],
        }

    return {
        "model": preferred_fallback,
        "reason": "No usable error metric",
    }


def evaluate_and_select(
    df: pd.DataFrame,
    candidates: Optional[
        Dict[str, ForecastFn]
    ] = None,
    horizon: int = 7,
    min_train_size: int = 14,
    step: int = 7,
) -> Dict[str, Any]:
    """
    Evaluate every available forecasting candidate and select the
    best out-of-sample model.
    """

    if candidates is None:
        candidates = default_candidates()

    comparison = compare_forecasters(
        df=df,
        candidates=candidates,
        horizon=horizon,
        min_train_size=min_train_size,
        step=step,
    )

    selection = select_best_model(
        comparison
    )

    return {
        "evaluation": comparison,
        "selection": selection,
    }


def forecast_quality_label(
    smape_value: Optional[float],
) -> str:
    """
    Human-readable quality band.

    This is descriptive rather than a guarantee of future accuracy.
    """

    if smape_value is None:
        return "unknown"

    if smape_value < 10:
        return "very_good"

    if smape_value < 20:
        return "good"

    if smape_value < 35:
        return "moderate"

    if smape_value < 50:
        return "weak"

    return "poor"