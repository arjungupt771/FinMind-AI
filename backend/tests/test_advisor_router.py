import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.database.config import get_db
from backend.dependencies import get_current_user_id
from backend.database.repositories import TransactionRepository
from backend.routers import advisor
from backend.services.financial_advisor import FinancialAdvisorService
from backend.services.gemini_service import AIResponse


@pytest.fixture
def advisor_test_app(db_session):
    """
    Create a minimal FastAPI application containing only the advisor router.

    The authentication dependency is overridden so that the test can
    deterministically verify which user ID reaches the advisor service.
    """

    app = FastAPI()

    app.include_router(
        advisor.router,
        prefix="/advisor",
    )

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user_id] = lambda: "authenticated-user"

    return app


def test_advisor_uses_authenticated_user_id(
    advisor_test_app,
    db_session,
    monkeypatch,
):
    """
    The advisor must use the authenticated user ID rather than accepting
    a user_id supplied by the client.

    A request containing an arbitrary user_id should therefore not affect
    which user's financial data is queried.
    """

    repo = TransactionRepository(db_session)

    repo.create(
        {
            "id": str(uuid.uuid4()),
            "user_id": "authenticated-user",
            "date": datetime(2026, 1, 1),
            "merchant": "Test Merchant",
            "amount": 100.0,
            "transaction_type": "expense",
            "category": "Food",
            "source": "test",
        }
    )

    captured = {}

    async def fake_answer_question(
        self,
        user_id,
        question,
        conversation_id=None,
    ):
        captured["user_id"] = user_id
        captured["question"] = question
        captured["conversation_id"] = conversation_id

        return {
            "summary": "Test summary",
            "insights": [],
            "recommendations": [],
            "risk_level": "LOW",
            "sources": [],
            "conversation_id": conversation_id or "test-conversation",
        }

    monkeypatch.setattr(
        FinancialAdvisorService,
        "answer_question",
        fake_answer_question,
    )

    client = TestClient(advisor_test_app)

    response = client.post(
        "/advisor/chat",
        json={
            "user_id": "attacker-selected-user",
            "question": "How am I doing?",
        },
    )

    assert response.status_code == 200

    assert captured["user_id"] == "authenticated-user"
    assert captured["user_id"] != "attacker-selected-user"
    assert captured["question"] == "How am I doing?"