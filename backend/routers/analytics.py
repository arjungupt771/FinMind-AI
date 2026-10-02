import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from backend.database.config import get_db
from backend.database.repositories import TransactionRepository
from backend.dependencies import get_current_user_id
from backend.analytics.anomaly_detection import detect_all_anomalies
from backend.forecasting.report import generate_forecast_evaluation_report, generate_full_analytics_report

logger = logging.getLogger(__name__)
router = APIRouter()


def _load_transaction_dicts(db: Session, user_id: str) -> List[Dict[str, Any]]:
    repo = TransactionRepository(db)
    txs = repo.get_user_transactions(user_id, limit=5000)
    return [tx.to_dict() for tx in txs]


@router.get('/anomalies')
async def get_anomalies(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    transactions = _load_transaction_dicts(db, user_id)
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions found for this user")
    return await detect_all_anomalies(transactions, user_id=user_id)


@router.get('/forecast-evaluation')
async def get_forecast_evaluation(
    metric_type: str = Query('expense', pattern='^(expense|income|savings)$'),
    horizon: int = Query(7, ge=1, le=90),
    granularity: str = Query('daily', pattern='^(daily|monthly)$'),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    transactions = _load_transaction_dicts(db, user_id)
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions found for this user")
    return await generate_forecast_evaluation_report(
        transactions, metric_type=metric_type, horizon=horizon, granularity=granularity, user_id=user_id
    )

@router.get('/report')
async def get_full_report(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    transactions = _load_transaction_dicts(db, user_id)
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions found for this user")
    return await generate_full_analytics_report(transactions, user_id=user_id)