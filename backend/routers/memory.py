from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.config import get_db
from backend.dependencies import get_current_user_id
from backend.services.financial_memory import (
    FinancialMemoryService,
)


router = APIRouter()


class MemoryCreate(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=2000,
    )

    memory_type: str = "financial_fact"

    source: str = "user"

    importance: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
    )

    confidence: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
    )


class MemoryResponse(BaseModel):
    id: str
    memory_type: str
    content: str
    source: str
    importance: float
    confidence: float
    active: bool


@router.get("/")
def list_memories(
    memory_type: Optional[str] = None,
    limit: int = 100,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = FinancialMemoryService(db)

    return {
        "memories": service.get_all(
            user_id=user_id,
            memory_type=memory_type,
            limit=min(limit, 100),
        )
    }


@router.post(
    "/",
    response_model=MemoryResponse,
)
def create_memory(
    payload: MemoryCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = FinancialMemoryService(db)

    try:
        return service.create_memory(
            user_id=user_id,
            content=payload.content,
            memory_type=payload.memory_type,
            source=payload.source,
            importance=payload.importance,
            confidence=payload.confidence,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.get("/search")
def search_memories(
    q: str,
    limit: int = 8,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = FinancialMemoryService(db)

    return {
        "query": q,
        "memories": service.retrieve(
            user_id=user_id,
            query=q,
            limit=min(limit, 20),
        ),
    }


@router.post("/remember")
def remember_message(
    message: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = FinancialMemoryService(db)

    memories = service.remember_message(
        user_id=user_id,
        message=message,
    )

    return {
        "created": len(memories),
        "memories": memories,
    }


@router.delete("/{memory_id}")
def delete_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = FinancialMemoryService(db)

    deleted = service.delete_memory(
        user_id=user_id,
        memory_id=memory_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Memory not found",
        )

    return {
        "message": "Memory deactivated",
        "id": memory_id,
    }