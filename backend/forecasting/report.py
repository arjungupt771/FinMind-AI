from typing import Any, Dict, Optional


def build_forecast_report(forecast_result, evaluation=None):
    forecast_result = forecast_result or {}
    evaluation = evaluation or {}

    forecast = forecast_result.get("forecast", [])
    method = forecast_result.get("method", "none")
    forecast_type = forecast_result.get("forecast_type", "unknown")
    horizon = forecast_result.get("horizon", "unknown")
    frequency = forecast_result.get("frequency", "M")

    values = [
        float(point.get("yhat", 0))
        for point in forecast
    ]

    lower_values = [
        float(point.get("yhat_lower", 0))
        for point in forecast
    ]

    upper_values = [
        float(point.get("yhat_upper", 0))
        for point in forecast
    ]

    total_forecast = sum(values)

    average_forecast = (
        total_forecast / len(values)
        if values
        else 0.0
    )

    evaluation_summary = None
    model_quality = "unknown"

    if evaluation:
        evaluation_summary = evaluation.get(
            "evaluation",
            evaluation,
        )

        selected = evaluation.get("selection", {})
        selected_model = selected.get("model")

        if selected_model:
            method = selected_model

        selected_stats = (
            evaluation_summary.get(selected_model, {})
            if selected_model
            else {}
        )

        smape = selected_stats.get("smape")

        if smape is not None:
            if smape < 10:
                model_quality = "very_good"
            elif smape < 20:
                model_quality = "good"
            elif smape < 35:
                model_quality = "moderate"
            elif smape < 50:
                model_quality = "weak"
            else:
                model_quality = "poor"

    return {
        "forecast_type": forecast_type,
        "horizon": horizon,
        "frequency": frequency,
        "method": method,
        "model_quality": model_quality,
        "periods": len(forecast),
        "total_forecast": round(total_forecast, 2),
        "average_forecast": round(average_forecast, 2),
        "minimum_forecast": (
            round(min(values), 2)
            if values
            else 0.0
        ),
        "maximum_forecast": (
            round(max(values), 2)
            if values
            else 0.0
        ),
        "confidence_interval": {
            "lower_total": round(
                sum(lower_values),
                2,
            ),
            "upper_total": round(
                sum(upper_values),
                2,
            ),
        },
        "forecast": forecast,
        "evaluation": evaluation_summary,
    }


def format_forecast_summary(report):
    forecast_type = report.get(
        "forecast_type",
        "financial",
    )

    horizon = report.get(
        "horizon",
        "unknown",
    )

    method = report.get(
        "method",
        "unknown",
    )

    total = report.get(
        "total_forecast",
        0,
    )

    quality = report.get(
        "model_quality",
        "unknown",
    )

    return (
        f"{forecast_type.title()} forecast for {horizon}: "
        f"expected total {total:.2f}. "
        f"Selected model: {method}. "
        f"Historical validation quality: {quality}."
    )


# ------------------------------------------------------------------
# Backward-compatible analytics functions
# ------------------------------------------------------------------


async def generate_forecast_evaluation_report(
    transactions,
    metric_type="expense",
    horizon=7,
    min_train_size=14,
    step=7,
    granularity="daily",
    forecast_result=None,
    evaluation=None,
    *args,
    **kwargs,
):
    """
    Backward-compatible report generator used by analytics.py.

    Phase 7 adds the richer build_forecast_report() API while keeping
    the existing analytics integration intact.

    Parameters
    ----------
    transactions:
        Historical transaction records.

    metric_type:
        Forecast metric, e.g. "expense" or "income".

    horizon:
        Number of future periods.

    min_train_size:
        Minimum number of historical periods required for evaluation.

    step:
        Evaluation step size.

    granularity:
        Time-series granularity, e.g. "daily" or "monthly".

    forecast_result:
        Optional pre-computed forecast result.

    evaluation:
        Optional pre-computed evaluation result.

    Notes
    -----
    The forecasting/evaluation pipeline may supply the actual
    forecast_result and evaluation objects. This wrapper primarily
    preserves the existing report API.
    """

    evaluation = evaluation or {}
    forecast_result = forecast_result or {}

    report = build_forecast_report(
        forecast_result=forecast_result,
        evaluation=evaluation,
    )

    return {
        "forecast_type": report["forecast_type"],
        "horizon": report["horizon"],
        "frequency": report["frequency"],
        "granularity": granularity,
        "metric_type": metric_type,
        "method": report["method"],
        "best_model": report["method"],
        "model_quality": report["model_quality"],
        "periods": report["periods"],
        "total_forecast": report["total_forecast"],
        "average_forecast": report["average_forecast"],
        "minimum_forecast": report["minimum_forecast"],
        "maximum_forecast": report["maximum_forecast"],
        "confidence_interval": report["confidence_interval"],
        "evaluation": report["evaluation"],
        "forecast": report["forecast"],
    }


def generate_full_analytics_report(
    analytics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Backward-compatible analytics report wrapper.

    Keeps the existing analytics router working while Phase 7
    introduces the new forecasting report structure.
    """

    analytics = analytics or {}

    forecast_result = analytics.get(
        "forecast",
        analytics.get("forecast_result", {}),
    )

    evaluation = analytics.get(
        "evaluation",
        analytics.get("forecast_evaluation"),
    )

    forecast_report = generate_forecast_evaluation_report(
        evaluation=evaluation,
        forecast_result=forecast_result,
    )

    report = dict(analytics)

    report["forecast_report"] = forecast_report

    return report