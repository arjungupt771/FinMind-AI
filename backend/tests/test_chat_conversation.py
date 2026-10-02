def _txs():
    return [
        {
            "date": "2026-09-01T00:00:00",
            "amount": 80000,
            "category": "Salary",
            "merchant": "Employer",
        },
        {
            "date": "2026-09-02T00:00:00",
            "amount": -400,
            "category": "Food",
            "merchant": "Swiggy",
        },
    ]


def test_chat_response_includes_conversation_id(
    client,
    monkeypatch,
):
    from unittest.mock import AsyncMock

    from backend.routers import chat
    from backend.services import gemini_service

    fake = gemini_service.AIResponse(
        summary="s",
        insights=[],
        recommendations=[],
        risk_level="LOW",
    )

    monkeypatch.setattr(
        chat,
        "analyze_spending",
        AsyncMock(return_value=fake),
    )

    resp = client.post(
        "/chat/",
        json={
            "question": "How am I doing?",
            "transactions": _txs(),
        },
    )

    assert resp.status_code == 200

    data = resp.json()

    assert data["conversation_id"]


def test_chat_persists_and_reuses_conversation_id(
    client,
    monkeypatch,
):
    from backend.routers import chat
    from backend.services import gemini_service

    captured = {}

    async def _fake(
        transactions,
        question=None,
        days=30,
        conversation_history=None,
    ):
        captured["history"] = conversation_history

        return gemini_service.AIResponse(
            summary="s2",
            insights=[],
            recommendations=[],
            risk_level="LOW",
        )

    monkeypatch.setattr(
        chat,
        "analyze_spending",
        _fake,
    )

    r1 = client.post(
        "/chat/",
        json={
            "question": "first",
            "transactions": _txs(),
        },
    )

    assert r1.status_code == 200

    conv_id = r1.json()["conversation_id"]

    assert conv_id

    r2 = client.post(
        "/chat/",
        json={
            "question": "second",
            "transactions": _txs(),
            "conversation_id": conv_id,
        },
    )

    assert r2.status_code == 200

    assert captured["history"] is not None

    assert any(
        h["question"] == "first"
        for h in captured["history"]
    )