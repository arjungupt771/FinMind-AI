"""
Shared FastAPI dependencies
"""
import os
from typing import Optional
from fastapi import Header, HTTPException, status

from backend.auth import decode_access_token


def get_current_user_id(
    authorization: Optional[str] = Header(default=None),
    x_user_id: str = Header(default="demo-user"),
) -> str:
    """
    A valid `Authorization: Bearer <jwt>` header always wins and identifies
    the real user. Falls back to the `X-User-Id` placeholder header for
    local/demo use UNLESS AUTH_REQUIRED=true, in which case a missing or
    invalid token is rejected outright. This keeps every existing demo flow
    working while giving you a real switch to flip for production.
    """
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        payload = decode_access_token(token)  # raises HTTPException(401) on invalid/expired
        return payload["sub"]

    environment = os.getenv(
        "ENVIRONMENT",
        "development",
    ).strip().lower()
    auth_required = environment not in {
        "development",
        "dev",
        "test",
        "testing",
    }

    if os.getenv("AUTH_REQUIRED") is not None:
        configured_value = os.getenv("AUTH_REQUIRED", "").strip().lower()
        if environment in {
            "development",
            "dev",
            "test",
            "testing",
        }:
            auth_required = configured_value in {
                "1",
                "true",
                "yes",
                "on",
            }

    if auth_required:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return x_user_id