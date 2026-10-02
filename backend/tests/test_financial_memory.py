from backend.services.financial_memory import (
    FinancialMemoryService,
)


def test_memory_extraction_detects_savings_goal(
    db_session,
):
    service = FinancialMemoryService(
        db_session
    )

    memories = service.extract_memories_from_message(
        "I want to save 5 lakh for a car."
    )

    assert memories

    assert any(
        memory["memory_type"] == "goal"
        for memory in memories
    )


def test_memory_extraction_detects_preference():
    service = FinancialMemoryService(None)

    memories = service.extract_memories_from_message(
        "I prefer keeping my emergency fund in cash."
    )

    assert memories

    assert any(
        memory["memory_type"] == "preference"
        for memory in memories
    )


def test_memory_extraction_detects_constraint():
    service = FinancialMemoryService(None)

    memories = service.extract_memories_from_message(
        "I cannot spend more than 20000 on shopping."
    )

    assert memories

    assert any(
        memory["memory_type"] == "constraint"
        for memory in memories
    )


def test_empty_message_returns_no_memory():
    service = FinancialMemoryService(None)

    memories = service.extract_memories_from_message("")

    assert memories == []


def test_tokenization_is_case_insensitive():
    tokens = FinancialMemoryService._tokenize(
        "Monthly Food Budget"
    )

    assert "monthly" in tokens
    assert "food" in tokens
    assert "budget" in tokens


def test_memory_types_are_defined():
    assert "goal" in (
        FinancialMemoryService.MEMORY_TYPES
    )

    assert "preference" in (
        FinancialMemoryService.MEMORY_TYPES
    )

    assert "constraint" in (
        FinancialMemoryService.MEMORY_TYPES
    )


def test_memory_retrieval_prioritizes_goal_context(db_session):
    service = FinancialMemoryService(db_session)

    service.create_memory(
        user_id="demo-user",
        content="I usually spend ₹200 on groceries every week.",
        memory_type="behavior",
        importance=0.6,
        confidence=0.8,
    )
    service.create_memory(
        user_id="demo-user",
        content="I want to save ₹5 lakh for a car.",
        memory_type="goal",
        importance=0.95,
        confidence=0.92,
    )

    results = service.retrieve(
        user_id="demo-user",
        query="How am I doing toward my car goal?",
        intent="goal",
        limit=5,
    )

    assert results
    assert results[0]["memory_type"] == "goal"


def test_memory_conflict_resolution_marks_older_goal_superseded(db_session):
    service = FinancialMemoryService(db_session)

    service.create_memory(
        user_id="demo-user",
        content="I want to save ₹5 lakh for a car.",
        memory_type="goal",
        importance=0.9,
        confidence=0.9,
    )

    service.create_memory(
        user_id="demo-user",
        content="I do not want to save for a car anymore.",
        memory_type="goal",
        importance=0.97,
        confidence=0.98,
    )

    active_memories = service.get_all(user_id="demo-user", memory_type="goal", include_inactive=True)
    superseded = [m for m in active_memories if m.get("status") == "superseded"]

    assert superseded
    assert not any(m["content"] == "I want to save ₹5 lakh for a car." and m["active"] for m in active_memories)
    assert any(m["content"] == "I do not want to save for a car anymore." and m["active"] for m in active_memories)