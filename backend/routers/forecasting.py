"""
Forecasting API.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.config import get_db
from backend.database.repositories import TransactionRepository
from backend.dependencies import get_current_user_id

from backend.forecasting.forecasting import (
    FinancialForecaster,
)
from backend.forecasting.evaluation import (
    default_candidates,
    evaluate_and_select,
)
from backend.forecasting.report import (
    build_forecast_report,
    format_forecast_summary,
)


router = APIRouter()


def _transaction_dict(tx) -> Dict[str, Any]:
    signed_amount = (
        abs(tx.amount)
        if tx.transaction_type == "income"
        else -abs(tx.amount)
    )

    return {
        "id": tx.id,
        "date": (
            tx.date.isoformat()
            if tx.date
            else None
        ),
        "merchant": tx.merchant,
        "amount": signed_amount,
        "type": tx.transaction_type,
        "transaction_type": tx.transaction_type,
        "category": tx.category,
        "source": tx.source,
        "description": tx.description,
    }


@router.get("/")
async def forecast(
    metric: str = Query(
        "expense",
        pattern="^(expense|income|savings)$",
    ),
    horizon: str = Query(
        "1m",
        pattern="^(1m|3m|6m|12m)$",
    ),
    frequency: str = Query(
        "M",
        pattern="^(D|M)$",
    ),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Generate a financial forecast.

    M = monthly forecast.
    D = daily forecast.
    """

    try:
        repo = TransactionRepository(db)

        transactions = repo.get_user_transactions(
            user_id=user_id,
            limit=10000,
        )

        transaction_dicts = [
            _transaction_dict(tx)
            for tx in transactions
        ]

        forecaster = FinancialForecaster()

        result = forecaster.forecast(
            transactions=transaction_dicts,
            metric_type=metric,
            horizon=horizon,
            frequency=frequency,
        )

        return {
            "user_id": user_id,
            **result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate forecast",
        ) from exc


@router.get("/report")
async def forecast_report(
    metric: str = Query(
        "expense",
        pattern="^(expense|income|savings)$",
    ),
    horizon: str = Query(
        "1m",
        pattern="^(1m|3m|6m|12m)$",
    ),
    frequency: str = Query(
        "M",
        pattern="^(D|M)$",
    ),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Generate a forecast plus structured report.
    """

    repo = TransactionRepository(db)

    transactions = repo.get_user_transactions(
        user_id=user_id,
        limit=10000,
    )

    transaction_dicts = [
        _transaction_dict(tx)
        for tx in transactions
    ]

    forecaster = FinancialForecaster()

    result = forecaster.forecast(
        transaction_dicts,
        metric_type=metric,
        horizon=horizon,
        frequency=frequency,
    )

    report = build_forecast_report(
        result
    )

    report["summary"] = (
        format_forecast_summary(
            report
        )
    )

    return {
        "user_id": user_id,
        "forecast": result,
        "report": report,
    }


@router.get("/evaluation")
async def forecast_evaluation(
    metric: str = Query(
        "expense",
        pattern="^(expense|income|savings)$",
    ),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Evaluate candidate models using historical walk-forward validation.
    """

    repo = TransactionRepository(db)

    transactions = repo.get_user_transactions(
        user_id=user_id,
        limit=10000,
    )

    transaction_dicts = [
        _transaction_dict(tx)
        for tx in transactions
    ]

    forecaster = FinancialForecaster()

    df = forecaster.prepare_monthly_data(
        transaction_dicts,
        metric,
    )

    if df.empty:
        return {
            "user_id": user_id,
            "metric": metric,
            "evaluation": {},
            "selection": {
                "model": "none",
                "reason": "No historical data",
            },
        }

    if len(df) < 21:
        return {
            "user_id": user_id,
            "metric": metric,
            "evaluation": {},
            "selection": {
                "model": "none",
                "reason": (
                    "At least 21 monthly observations "
                    "are recommended for evaluation"
                ),
            },
        }

    result = evaluate_and_select(
        df=df,
        candidates=default_candidates(
            forecaster
        ),
        horizon=3,
        min_train_size=12,
        step=3,
    )

    return {
        "user_id": user_id,
        "metric": metric,
        **result,
    }