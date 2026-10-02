from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

from backend.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    create_access_token,
    decode_access_token,
    verify_password,
)


def test_register_and_login_flow(client):
    resp = client.post("/auth/register", json={"email": "a@example.com", "password": "secret123"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]

    resp2 = client.post("/auth/login", json={"email": "a@example.com", "password": "secret123"})
    assert resp2.status_code == 200
    token2 = resp2.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token2}"})
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"


def test_register_duplicate_email_rejected(client):
    client.post("/auth/register", json={"email": "dup@example.com", "password": "secret123"})
    resp = client.post("/auth/register", json={"email": "dup@example.com", "password": "other123"})
    assert resp.status_code == 400


def test_login_wrong_password_rejected(client):
    client.post("/auth/register", json={"email": "b@example.com", "password": "rightpass"})
    resp = client.post("/auth/login", json={"email": "b@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_demo_fallback_still_works_without_auth_required(client):
    resp = client.get("/transactions/")
    assert resp.status_code == 200


def test_auth_required_env_enforced(client, monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    try:
        resp = client.get("/transactions/")
        assert resp.status_code == 401
    finally:
        monkeypatch.delenv("AUTH_REQUIRED", raising=False)


def test_bearer_token_correctly_scopes_transactions(client):
    reg = client.post("/auth/register", json={"email": "c@example.com", "password": "pass1234"})
    token = reg.json()["access_token"]

    client.post(
        "/transactions/",
        json={"date": "2026-09-01T00:00:00", "merchant": "M", "amount": 100,
              "type": "expense", "category": "Food", "source": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )

    as_user = client.get("/transactions/", headers={"Authorization": f"Bearer {token}"})
    assert len(as_user.json()) == 1

    as_demo = client.get("/transactions/")  # no token → falls back to demo-user
    assert as_demo.json() == []


def test_production_requires_authentication_by_default(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("AUTH_REQUIRED", raising=False)

    response = client.get(
        "/transactions/",
        headers={"X-User-Id": "another-user"},
    )

    assert response.status_code == 401


def test_invalid_bearer_token_is_rejected(client):
    response = client.get(
        "/transactions/",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_decode_rejects_expired_or_incomplete_tokens():
    expired_token = jwt.encode(
        {
            "sub": "user-1",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    missing_exp_token = jwt.encode(
        {"sub": "user-1"},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    missing_sub_token = jwt.encode(
        {
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    for token in (
        expired_token,
        missing_exp_token,
        missing_sub_token,
    ):
        with pytest.raises(HTTPException) as error:
            decode_access_token(token)
        assert error.value.status_code == 401


def test_extra_claims_cannot_override_reserved_claims():
    with pytest.raises(ValueError):
        create_access_token(
            "user-1",
            extra_claims={"sub": "another-user"},
        )


def test_malformed_password_hash_fails_closed():
    assert verify_password("secret", "not-a-valid-hash") is False


@pytest.mark.parametrize(
    "password",
    [
        "short",
        "é" * 37,
    ],
)
def test_register_rejects_weak_or_overlong_passwords(client, password):
    response = client.post(
        "/auth/register",
        json={
            "email": "password-boundary@example.com",
            "password": password,
        },
    )

    assert response.status_code == 422


def test_demo_user_is_not_seeded_outside_development(monkeypatch):
    import backend.main as main_module

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(
        main_module,
        "SessionLocal",
        lambda: pytest.fail("Production must not seed the demo user"),
    )

    main_module._ensure_demo_user()