from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.config import get_db
from backend.dependencies import get_current_user_id
from backend.services.financial_advisor import (
    FinancialAdvisorService,
)


router = APIRouter()


class AdvisorRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=4000,
    )
    conversation_id: Optional[str] = None


@router.post("/chat")
async def advisor_chat(
    request: AdvisorRequest,
    user_id: str = Depends(
        get_current_user_id
    ),
    db: Session = Depends(get_db),
):
    advisor_service = FinancialAdvisorService(db)

    result = await advisor_service.answer_question(
        user_id=user_id,
        question=request.question,
        conversation_id=request.conversation_id,
    )

    return {
        "success": True,
        "data": result,
    }


@router.get("/conversation/{conversation_id}")
def get_conversation(
    conversation_id: str,
    user_id: str = Depends(
        get_current_user_id
    ),
    db: Session = Depends(get_db),
):
    history = (
        FinancialAdvisorService(db)
        .chat_history_repo
        .get_user_history(
            user_id=user_id,
            conversation_id=conversation_id,
            limit=50,
        )
    )

    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "id": row.id,
                "question": row.message,
                "answer": row.response,
                "analysis_type": row.analysis_type,
                "created_at": (
                    row.created_at.isoformat()
                    if row.created_at
                    else None
                ),
            }
            for row in reversed(history)
        ],
    }