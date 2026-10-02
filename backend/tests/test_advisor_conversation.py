import uuid
from datetime import datetime
import pytest
from unittest.mock import AsyncMock

from backend.services.financial_advisor import FinancialAdvisorService
from backend.services.gemini_service import AIResponse
from backend.database.repositories import TransactionRepository


@pytest.mark.asyncio
async def test_answer_question_persists_conversation_and_returns_sources(db_session):
    repo = TransactionRepository(db_session)
    repo.create({
        "id": str(uuid.uuid4()),
        "user_id": "demo-user",
        "date": datetime(2026, 1, 1),
        "merchant": "Test",
        "amount": 100.0,
        "transaction_type": "expense",
        "category": "Food",
        "source": "test",
    })

    service = FinancialAdvisorService(db_session)
    service.gemini.financial_advisor_response = AsyncMock(return_value=AIResponse(
        summary="Test summary", insights=["i1"], recommendations=["r1"], risk_level="LOW"
    ))

    result = await service.answer_question("demo-user", "How am I doing?")

    assert result["summary"] == "Test summary"
    assert "conversation_id" in result
    assert result["sources"] == []  # no chromadb data seeded in this test — empty, not missing

    history = service.chat_history_repo.get_user_history("demo-user", conversation_id=result["conversation_id"])
    assert len(history) == 1
    assert history[0].message == "How am I doing?"


@pytest.mark.asyncio
async def test_answer_question_reuses_provided_conversation_id(db_session):
    service = FinancialAdvisorService(db_session)
    service.gemini.financial_advisor_response = AsyncMock(return_value=AIResponse(
        summary="s", insights=[], recommendations=[], risk_level="LOW"
    ))

    result = await service.answer_question("demo-user", "q1", conversation_id="conv-abc")
    assert result["conversation_id"] == "conv-abc"


@pytest.mark.asyncio
async def test_second_turn_sees_first_turn_as_conversation_history(db_session, monkeypatch):
    service = FinancialAdvisorService(db_session)
    captured_history = {}

    async def _fake_response(question, context, conversation_history=None):
        captured_history["value"] = conversation_history
        return AIResponse(summary="ok", insights=[], recommendations=[], risk_level="LOW")

    service.gemini.financial_advisor_response = AsyncMock(side_effect=_fake_response)

    await service.answer_question("demo-user", "first question", conversation_id="conv-1")
    await service.answer_question("demo-user", "second question", conversation_id="conv-1")

    # by the second call, the first turn should have been passed in as history
    assert captured_history["value"] is not None
    assert any(h["question"] == "first question" for h in captured_history["value"])


@pytest.mark.asyncio
async def test_answer_question_cites_flagged_transactions(db_session):
    import uuid
    from datetime import datetime
    from unittest.mock import AsyncMock
    from backend.database.repositories import TransactionRepository
    from backend.services.financial_advisor import FinancialAdvisorService
    from backend.services.gemini_service import AIResponse

    repo = TransactionRepository(db_session)
    for d in range(1, 10):
        repo.create({
            "id": str(uuid.uuid4()), "user_id": "demo-user", "date": datetime(2026, 1, d),
            "merchant": "M", "amount": 100.0, "transaction_type": "expense",
            "category": "Food", "source": "test",
        })
    repo.create({
        "id": str(uuid.uuid4()), "user_id": "demo-user", "date": datetime(2026, 1, 10),
        "merchant": "BigSpike", "amount": 5000.0, "transaction_type": "expense",
        "category": "Food", "source": "test",
    })

    service = FinancialAdvisorService(db_session)
    service.gemini.financial_advisor_response = AsyncMock(return_value=AIResponse(
        summary="s", insights=[], recommendations=[], risk_level="LOW"
    ))

    result = await service.answer_question("demo-user", "anything flagged?")
    transaction_sources = [s for s in result["sources"] if s["source_type"] == "transaction"]
    assert any(s["merchant"] == "BigSpike" for s in transaction_sources)


@pytest.mark.asyncio
async def test_advisor_remembers_goal_for_later_context(
    db_session,
    monkeypatch,
):
    import backend.services.financial_advisor as financial_advisor_module

    async def _empty_rag_context(*, user_id, question):
        return "", []

    monkeypatch.setattr(
        financial_advisor_module,
        "retrieve_context_with_citations",
        _empty_rag_context,
    )

    service = FinancialAdvisorService(db_session)
    service.gemini.financial_advisor_response = AsyncMock(
        return_value=AIResponse(
            summary="Understood",
            insights=[],
            recommendations=[],
            risk_level="LOW",
        )
    )

    await service.answer_question(
        "demo-user",
        "I want to save 500000 for a car.",
    )

    memories = service.memory_service.get_all(
        user_id="demo-user",
        memory_type="goal",
    )
    assert len(memories) == 1

    await service.answer_question(
        "demo-user",
        "Can I afford this?",
    )

    context = (
        service.gemini.financial_advisor_response
        .await_args.kwargs["context"]
    )
    assert "i want to save 500000 for a car." in context[
        "relevant_past_context"
    ]


@pytest.mark.asyncio
async def test_advisor_includes_goal_context(db_session, monkeypatch):
    from datetime import datetime, timedelta

    import backend.services.financial_advisor as financial_advisor_module
    from backend.database.repositories import GoalRepository

    async def _empty_memory(*, user_id, question):
        return "", []

    monkeypatch.setattr(
        financial_advisor_module,
        "retrieve_context_with_citations",
        _empty_memory,
    )

    GoalRepository(db_session).create({
        "id": str(uuid.uuid4()),
        "user_id": "demo-user",
        "name": "Emergency Fund",
        "description": "Build emergency savings",
        "category": "Emergency",
        "target_amount": 100000,
        "current_amount": 25000,
        "deadline": datetime.utcnow() + timedelta(days=180),
        "priority": 5,
        "status": "active",
    })

    service = FinancialAdvisorService(db_session)
    service.gemini.financial_advisor_response = AsyncMock(
        return_value=AIResponse(
            summary="Goal context received",
            insights=[],
            recommendations=[],
            risk_level="LOW",
        )
    )

    result = await service.answer_question(
        "demo-user",
        "How am I doing?",
    )

    call_context = (
        service.gemini.financial_advisor_response
        .await_args.kwargs["context"]
    )
    assert call_context["goals"]["goal_count"] == 1
    assert call_context["goals"]["goals"][0]["name"] == "Emergency Fund"
    assert "goals" in call_context["copilot"]["context_used"]
    assert any(
        source.get("name") == "Emergency Fund"
        for source in result["sources"]
    )