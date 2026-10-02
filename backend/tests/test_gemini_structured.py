import pytest

from backend.services.gemini_service import parse_structured_response


def test_parse_structured_response_valid_json():
    raw = '{"summary": "ok", "insights": ["a"], "recommendations": ["b"], "risk_level": "LOW"}'
    result = parse_structured_response(raw)
    assert result.summary == "ok"


def test_parse_structured_response_falls_back_on_fenced_json():
    raw = '```json\n{"summary": "ok2", "insights": [], "recommendations": [], "risk_level": "MEDIUM"}\n```'
    result = parse_structured_response(raw)
    assert result.summary == "ok2"


def test_parse_structured_response_falls_back_to_default_on_garbage():
    result = parse_structured_response("not json")
    assert result.risk_level == "MEDIUM"
    assert result.confidence == 0.5


@pytest.mark.asyncio
async def test_generate_structured_response_falls_back_when_structured_call_raises(monkeypatch):
    from backend.services import gemini_service

    async def _raise_structured(*args, **kwargs):
        raise RuntimeError("schema not supported by this SDK version")

    async def _fake_plain(*args, **kwargs):
        return '{"summary": "fallback worked", "insights": [], "recommendations": [], "risk_level": "LOW"}'

    monkeypatch.setattr(gemini_service, "call_gemini_api_structured", _raise_structured)
    monkeypatch.setattr(gemini_service, "call_gemini_api", _fake_plain)

    result = await gemini_service.generate_structured_response("any prompt")
    assert result.summary == "fallback worked"