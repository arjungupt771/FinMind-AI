import pytest
from backend.rag.rag_service import _require_user_id, _user_where


def test_require_user_id_rejects_empty_or_none():
    with pytest.raises(ValueError):
        _require_user_id("")
    with pytest.raises(ValueError):
        _require_user_id(None)


def test_require_user_id_accepts_valid():
    assert _require_user_id("user-123") == "user-123"


def test_user_where_always_scopes_by_user():
    assert _user_where("user-123") == {"user_id": {"$eq": "user-123"}}


def test_user_where_combines_with_extra_filter():
    where = _user_where("user-123", {"category": {"$eq": "Food"}})
    assert where["$and"][0] == {"user_id": {"$eq": "user-123"}}
    assert where["$and"][1] == {"category": {"$eq": "Food"}}


def test_user_where_rejects_missing_user_id_even_with_extra_filter():
    with pytest.raises(ValueError):
        _user_where(None, {"category": {"$eq": "Food"}})