import uuid
from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.config import get_db
from backend.database.repositories import (
    GoalRepository,
    TransactionRepository,
)
from backend.dependencies import get_current_user_id
from backend.services.goal_intelligence import GoalIntelligence


router = APIRouter()


class GoalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    target_amount: float = Field(..., gt=0)
    current_amount: float = Field(
        default=0,
        ge=0,
    )
    deadline: str
    priority: int = Field(
        default=1,
        ge=1,
        le=10,
    )


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    target_amount: Optional[float] = Field(
        default=None,
        gt=0,
    )
    current_amount: Optional[float] = Field(
        default=None,
        ge=0,
    )
    deadline: Optional[str] = None
    priority: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
    )
    status: Optional[str] = None


class GoalContribution(BaseModel):
    amount: float = Field(..., gt=0)


def _serialize_goal(goal):
    return {
        "id": goal.id,
        "user_id": goal.user_id,
        "name": goal.name,
        "description": goal.description,
        "category": goal.category,
        "target_amount": goal.target_amount,
        "current_amount": goal.current_amount,
        "deadline": (
            goal.deadline.isoformat()
            if goal.deadline
            else None
        ),
        "priority": goal.priority,
        "status": goal.status,
        "created_at": (
            goal.created_at.isoformat()
            if goal.created_at
            else None
        ),
        "updated_at": (
            goal.updated_at.isoformat()
            if goal.updated_at
            else None
        ),
    }


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).replace(tzinfo=None)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid deadline. Use ISO format.",
        ) from exc


def _get_owned_goal(
    goal_id: str,
    user_id: str,
    db: Session,
):
    goal = GoalRepository(db).get_by_id(goal_id)

    if not goal or goal.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail="Goal not found",
        )

    return goal


@router.get("/")
def list_goals(
    status: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goals = GoalRepository(db).get_user_goals(
        user_id=user_id,
        status=status,
    )

    return {
        "count": len(goals),
        "goals": [
            _serialize_goal(goal)
            for goal in goals
        ],
    }


@router.post("/")
def create_goal(
    payload: GoalCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    deadline = _parse_datetime(payload.deadline)

    if deadline <= datetime.now():
        raise HTTPException(
            status_code=422,
            detail="Goal deadline must be in the future",
        )

    goal = GoalRepository(db).create({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": payload.name,
        "description": payload.description,
        "category": payload.category,
        "target_amount": payload.target_amount,
        "current_amount": payload.current_amount,
        "deadline": deadline,
        "priority": payload.priority,
        "status": "active",
    })

    return {
        "success": True,
        "goal": _serialize_goal(goal),
    }


@router.get("/intelligence")
def goal_intelligence(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal_repo = GoalRepository(db)
    transaction_repo = TransactionRepository(db)

    goals = goal_repo.get_user_goals(
        user_id=user_id,
    )

    transactions = transaction_repo.get_user_transactions(
        user_id=user_id,
        limit=10000,
    )

    transaction_dicts = [
        tx.to_dict()
        for tx in transactions
    ]

    intelligence = GoalIntelligence().analyze_all(
        goals,
        transaction_dicts,
    )

    return {
        "success": True,
        "data": intelligence,
    }


@router.get("/{goal_id}")
def get_goal(
    goal_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = _get_owned_goal(
        goal_id,
        user_id,
        db,
    )

    transactions = TransactionRepository(
        db
    ).get_user_transactions(
        user_id=user_id,
        limit=10000,
    )

    analysis = GoalIntelligence().analyze_goal(
        goal,
        [tx.to_dict() for tx in transactions],
    )

    return {
        "goal": _serialize_goal(goal),
        "intelligence": analysis,
    }


@router.put("/{goal_id}")
def update_goal(
    goal_id: str,
    payload: GoalUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = _get_owned_goal(
        goal_id,
        user_id,
        db,
    )

    updates = payload.model_dump(
        exclude_unset=True
    )

    if "deadline" in updates:
        updates["deadline"] = _parse_datetime(
            updates["deadline"]
        )

    if (
        "target_amount" in updates
        and updates["target_amount"] <= 0
    ):
        raise HTTPException(
            status_code=422,
            detail="target_amount must be greater than zero",
        )

    updated = GoalRepository(db).update(
        goal_id,
        updates,
    )

    return {
        "success": True,
        "goal": _serialize_goal(updated),
    }


@router.post("/{goal_id}/contribution")
def add_contribution(
    goal_id: str,
    payload: GoalContribution,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    goal = _get_owned_goal(
        goal_id,
        user_id,
        db,
    )

    new_amount = (
        float(goal.current_amount or 0)
        + payload.amount
    )

    status = (
        "completed"
        if new_amount >= goal.target_amount
        else goal.status
    )

    updated = GoalRepository(db).update(
        goal_id,
        {
            "current_amount": new_amount,
            "status": status,
        },
    )

    return {
        "success": True,
        "goal": _serialize_goal(updated),
    }


@router.delete("/{goal_id}")
def delete_goal(
    goal_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_owned_goal(
        goal_id,
        user_id,
        db,
    )

    deleted = GoalRepository(db).delete(
        goal_id
    )

    return {
        "success": deleted,
        "goal_id": goal_id,
    }