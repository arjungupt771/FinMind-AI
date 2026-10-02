import uuid
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.config import get_db
from backend.database.repositories import ChatHistoryRepository
from backend.dependencies import get_current_user_id
from backend.services.gemini_service import (
    analyze_spending,
    get_savings_recommendations,
    get_investment_suggestions,
    plan_goals,
    optimize_budget,
    generate_monthly_review,
    explain_financial_health,
    AIResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request with financial context"""
    question: str
    transactions: List[Dict[str, Any]]
    analysis_type: Optional[str] = "general"
    context: Optional[Dict[str, Any]] = None
    goals: Optional[List[Dict]] = None
    health_score: Optional[float] = None
    conversation_id: Optional[str] = None  # only meaningful for "general"/"spending"; omit to start fresh


class ChatResponse(BaseModel):
    """Structured chat response"""
    answer: str
    summary: str
    insights: List[str]
    recommendations: List[str]
    risk_level: str
    action_items: List[str]
    confidence: float
    conversation_id: str


@router.post('/', response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Main chat endpoint with intelligent routing to specialized analyzers.
    Every call is logged to chat_history; only the free-text "general"/
    "spending" path actually re-reads that history for continuity, since
    the other analysis types are one-shot reports, not conversations.
    """
    try:
        analysis_type = request.analysis_type or "general"

        if not request.transactions:
            raise ValueError("No transaction data provided")

        conversation_id = request.conversation_id or str(uuid.uuid4())
        chat_history_repo = ChatHistoryRepository(db)

        ai_response: Optional[AIResponse] = None

        if analysis_type == "savings":
            ai_response = await get_savings_recommendations(request.transactions)
        elif analysis_type == "investment":
            budget = request.context.get("monthly_budget") if request.context else None
            ai_response = await get_investment_suggestions(request.transactions, budget)
        elif analysis_type == "goals" and request.goals:
            ai_response = await plan_goals(request.transactions, request.goals)
        elif analysis_type == "budget":
            ai_response = await optimize_budget(request.transactions)
        elif analysis_type == "review":
            month = request.context.get("month") if request.context else None
            ai_response = await generate_monthly_review(request.transactions, month)
        elif analysis_type == "health" and request.health_score is not None:
            ai_response = await explain_financial_health(request.transactions, request.health_score)
        else:  # "general" or "spending" — the one conversational path
            history_rows = chat_history_repo.get_user_history(
                user_id, conversation_id=conversation_id, limit=5
            )
            conversation_history = [
                {"question": row.message, "answer": row.response}
                for row in reversed(history_rows)
            ]
            ai_response = await analyze_spending(
                request.transactions, request.question, conversation_history=conversation_history
            )

        chat_history_repo.create({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "message": request.question,
            "response": ai_response.summary,
            "analysis_type": analysis_type,
        })

        return ChatResponse(
            answer=ai_response.summary,
            summary=ai_response.summary,
            insights=ai_response.insights,
            recommendations=ai_response.recommendations,
            risk_level=ai_response.risk_level,
            action_items=ai_response.action_items,
            confidence=ai_response.confidence,
            conversation_id=conversation_id,
        )

    except ValueError as ve:
        logger.warning(
            "Chat validation failed (error_type=%s)",
            type(ve).__name__,
        )
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(
            "Chat request failed (error_type=%s)",
            type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail="Error processing chat request",
        ) from e


@router.post('/analyze-spending', response_model=ChatResponse)
async def analyze_spending_endpoint(request: ChatRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    request.analysis_type = "spending"
    return await chat(request, user_id=user_id, db=db)


@router.post('/savings-recommendations', response_model=ChatResponse)
async def savings_recommendations_endpoint(request: ChatRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    request.analysis_type = "savings"
    return await chat(request, user_id=user_id, db=db)


@router.post('/investment-suggestions', response_model=ChatResponse)
async def investment_suggestions_endpoint(request: ChatRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    request.analysis_type = "investment"
    return await chat(request, user_id=user_id, db=db)


@router.post('/goal-planning', response_model=ChatResponse)
async def goal_planning_endpoint(request: ChatRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    request.analysis_type = "goals"
    return await chat(request, user_id=user_id, db=db)


@router.post('/budget-optimization', response_model=ChatResponse)
async def budget_optimization_endpoint(request: ChatRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    request.analysis_type = "budget"
    return await chat(request, user_id=user_id, db=db)


@router.post('/monthly-review', response_model=ChatResponse)
async def monthly_review_endpoint(request: ChatRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    request.analysis_type = "review"
    return await chat(request, user_id=user_id, db=db)


@router.post('/financial-health', response_model=ChatResponse)
async def financial_health_endpoint(request: ChatRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if request.health_score is None:
        raise HTTPException(status_code=400, detail="health_score is required")
    request.analysis_type = "health"
    return await chat(request, user_id=user_id, db=db)