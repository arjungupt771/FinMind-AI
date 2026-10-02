 
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from backend.services.financial_intelligence import FinancialIntelligenceEngine
from backend.analytics.health_score import FinancialHealthScore
from backend.analytics.anomaly_detection import AnomalyDetector

logger = logging.getLogger(__name__)


class TransactionContext(BaseModel):
    recent_transactions: List[Dict[str, Any]]
    total_income: float
    total_expense: float
    savings_rate: float
    top_categories: List[Dict[str, Any]]
    emergency_fund_months: float
    investment_ratio: float
    average_monthly_expense: float
    period_days: int


class FinancialContext(BaseModel):
    transaction_summary: TransactionContext
    health: Dict[str, Any]
    top_anomalies: List[Dict[str, Any]]
    forecast: Optional[Dict[str, Any]] = None

    def to_prompt_dict(self) -> Dict[str, Any]:
        """Flattened, JSON-serializable view for embedding directly into a prompt."""
        return {
            "transaction_summary": self.transaction_summary.model_dump(),
            "financial_health": self.health,
            "flagged_anomalies": self.top_anomalies,
            "latest_forecast": self.forecast,
        }


def build_transaction_context(transactions: List[Dict], days: int = 30) -> TransactionContext:
    """Build structured transaction context for prompts"""
    if not transactions:
        return TransactionContext(
            recent_transactions=[],
            total_income=0,
            total_expense=0,
            savings_rate=0,
            top_categories=[],
            emergency_fund_months=0,
            investment_ratio=0,
            average_monthly_expense=0,
            period_days=days
        )

    cutoff_date = datetime.now() - timedelta(days=days)
    recent_txs = []
    for tx in transactions:
        raw_date = tx.get("date")
        if not raw_date:
            continue
        try:
            tx_date = datetime.fromisoformat(raw_date)
        except (ValueError, TypeError):
            continue
        if tx_date >= cutoff_date:
            recent_txs.append(tx)

    engine = FinancialIntelligenceEngine(
        period_days=days
    )

    intelligence = engine.analyze(transactions)

    income = intelligence.total_income
    expense = intelligence.total_expense
    savings_rate = intelligence.savings_rate
    investment_ratio = intelligence.investment_ratio

    top_categories = [
        {
            "category": item.category,
            "amount": item.amount,
        }
        for item in intelligence.top_categories[:5]
    ]

    formatted_txs = [
        {
            "date": tx["date"],
            "merchant": tx.get("merchant", "Unknown"),
            "amount": tx["amount"],
            "category": tx.get("category", "Other")
        }
        for tx in sorted(recent_txs, key=lambda x: x["date"], reverse=True)[:10]
    ]

    num_months = max(1, days // 30)
    avg_monthly_expense = expense / num_months

    savings = intelligence.net_cash_flow

    emergency_fund_months = (
        savings / avg_monthly_expense
        if avg_monthly_expense > 0
        else 0
    )

    return TransactionContext(
        recent_transactions=formatted_txs,
        total_income=income,
        total_expense=expense,
        savings_rate=savings_rate,
        top_categories=top_categories,
        emergency_fund_months=round(emergency_fund_months, 2),
        investment_ratio=investment_ratio,
        average_monthly_expense=avg_monthly_expense,
        period_days=days
    )


def build_financial_context(
    transactions: List[Dict[str, Any]],
    days: int = 30,
    max_anomalies: int = 5,
) -> FinancialContext:
    """
    The one function every LLM-facing code path should call to get its numbers.
    Combines spend aggregation + health score + top anomalies into a single
    object; callers that also have a stored forecast should set `.forecast`
    on the result afterward (it's a plain mutable field).
    """
    transaction_summary = build_transaction_context(transactions, days=days)

    health_engine = FinancialHealthScore()
    health = health_engine.calculate(transactions)

    detector = AnomalyDetector()
    ranked = detector.score_transactions(transactions)
    top_anomalies = ranked[:max_anomalies]

    return FinancialContext(
        transaction_summary=transaction_summary,
        health=health,
        top_anomalies=top_anomalies,
    )