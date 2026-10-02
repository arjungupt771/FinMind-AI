"""
Subscription and recurring-expense API.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.config import get_db
from backend.database.repositories import (
    SubscriptionRepository,
    TransactionRepository,
)
from backend.dependencies import get_current_user_id
from backend.services.recurring_expense_intelligence import (
    RecurringExpenseIntelligence,
)


router = APIRouter()


def _transaction_dict(tx) -> Dict[str, Any]:
    return {
        "id": tx.id,
        "date": tx.date.isoformat()
        if tx.date
        else None,
        "merchant": tx.merchant,
        "amount": (
            abs(tx.amount)
            if tx.transaction_type == "income"
            else -abs(tx.amount)
        ),
        "type": tx.transaction_type,
        "transaction_type": tx.transaction_type,
        "category": tx.category,
        "source": tx.source,
        "description": tx.description,
    }


@router.get("/intelligence")
def recurring_expense_intelligence(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Detect recurring expenses from transaction history.
    """

    try:
        transaction_repo = TransactionRepository(db)

        transactions = (
            transaction_repo.get_user_transactions(
                user_id=user_id,
                limit=10000,
            )
        )

        transaction_dicts = [
            _transaction_dict(tx)
            for tx in transactions
        ]

        intelligence = (
            RecurringExpenseIntelligence()
            .analyze(transaction_dicts)
        )

        return {
            "user_id": user_id,
            "intelligence": intelligence,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze recurring expenses",
        ) from exc


@router.get("/")
def list_subscriptions(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Return stored subscription records.
    """

    repo = SubscriptionRepository(db)

    subscriptions = repo.get_user_subscriptions(
        user_id=user_id,
    )

    return [
        {
            "id": subscription.id,
            "name": subscription.name,
            "merchant": subscription.merchant,
            "amount_per_cycle": subscription.amount_per_cycle,
            "cycle": subscription.cycle,
            "category": subscription.category,
            "status": subscription.status,
            "detected_date": (
                subscription.detected_date.isoformat()
                if subscription.detected_date
                else None
            ),
            "last_transaction_date": (
                subscription.last_transaction_date.isoformat()
                if subscription.last_transaction_date
                else None
            ),
            "cancellation_recommended": (
                subscription.cancellation_recommended
            ),
            "potential_savings": (
                subscription.potential_savings
            ),
        }
        for subscription in subscriptions
    ]


@router.get("/summary")
def subscription_summary(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Return stored subscription cost summary.
    """

    repo = SubscriptionRepository(db)

    subscriptions = repo.get_user_subscriptions(
        user_id=user_id,
    )

    monthly_cost = repo.get_total_monthly_cost(
        user_id=user_id,
    )

    annual_cost = monthly_cost * 12

    potential_savings = sum(
        float(subscription.potential_savings or 0)
        for subscription in subscriptions
        if subscription.cancellation_recommended
    )

    return {
        "active_subscription_count": len(
            subscriptions
        ),
        "monthly_cost": round(
            monthly_cost,
            2,
        ),
        "annual_cost": round(
            annual_cost,
            2,
        ),
        "potential_savings": round(
            potential_savings,
            2,
        ),
    }