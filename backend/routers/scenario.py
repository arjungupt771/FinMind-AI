from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.config import get_db
from backend.database.repositories import GoalRepository, TransactionRepository
from backend.dependencies import get_current_user_id
from backend.services.goal_intelligence import GoalIntelligence
from backend.services.decision_intelligence import ScenarioEngine, RecommendationEngine, CrossDomainIntelligenceEngine

router = APIRouter()


class ScenarioRequest(BaseModel):
    income_change: float = Field(default=0.0)
    expense_change: float = Field(default=0.0)
    savings_change: float = Field(default=0.0)
    subscription_removal: float = Field(default=0.0)


@router.post("/evaluate")
def evaluate_scenario(
    payload: ScenarioRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    repo = TransactionRepository(db)
    goal_repo = GoalRepository(db)

    transactions = [
        tx.to_dict()
        for tx in repo.get_user_transactions(user_id=user_id, limit=10000)
    ]
    goals = goal_repo.get_user_goals(user_id=user_id)

    result = ScenarioEngine().evaluate(transactions, goals, payload.model_dump())
    return {"success": True, "data": result}


@router.get("/recommendations")
def recommendation_summary(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    repo = TransactionRepository(db)
    goal_repo = GoalRepository(db)

    transactions = [
        tx.to_dict()
        for tx in repo.get_user_transactions(user_id=user_id, limit=10000)
    ]
    goals = goal_repo.get_user_goals(user_id=user_id)

    result = RecommendationEngine().generate(transactions, goals)
    return {"success": True, "data": result}


@router.get("/cross-domain")
def cross_domain_intelligence(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    repo = TransactionRepository(db)
    goal_repo = GoalRepository(db)

    transactions = [
        tx.to_dict()
        for tx in repo.get_user_transactions(user_id=user_id, limit=10000)
    ]
    goals = goal_repo.get_user_goals(user_id=user_id)

    goal_analysis = GoalIntelligence().analyze_all(goals, transactions)
    result = CrossDomainIntelligenceEngine().analyze(transactions, goals=goal_analysis.get("goals", []))
    return {"success": True, "data": result}
