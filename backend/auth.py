"""
Password hashing + JWT issuing/verification.
"""
import os
import logging
import secrets
from datetime import timedelta
from backend.utils.datetime import utcnow
from typing import Optional
from dotenv import load_dotenv
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status

load_dotenv()

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "development",
).strip().lower()
PRODUCTION_ENVIRONMENTS = {
    "production",
    "prod",
    "staging",
}
AUTH_REQUIRED_TRUE_VALUES = {
    "1",
    "true",
    "yes",
    "on",
}
AUTH_REQUIRED_FALSE_VALUES = {
    "0",
    "false",
    "no",
    "off",
}

configured_auth_required = os.getenv("AUTH_REQUIRED")
if configured_auth_required is not None:
    normalized_auth_required = configured_auth_required.strip().lower()
    if normalized_auth_required not in (
        AUTH_REQUIRED_TRUE_VALUES
        | AUTH_REQUIRED_FALSE_VALUES
    ):
        raise RuntimeError(
            "AUTH_REQUIRED must be a boolean value"
        )
    if (
        ENVIRONMENT in PRODUCTION_ENVIRONMENTS
        and normalized_auth_required in AUTH_REQUIRED_FALSE_VALUES
    ):
        raise RuntimeError(
            "AUTH_REQUIRED cannot be disabled outside development/test"
        )

configured_secret = os.getenv("JWT_SECRET_KEY", "").strip()
is_placeholder_secret = (
    "change-me" in configured_secret.lower()
    or configured_secret.lower().startswith("your_")
)

if ENVIRONMENT in PRODUCTION_ENVIRONMENTS:
    if (
        len(configured_secret.encode("utf-8")) < 32
        or is_placeholder_secret
    ):
        raise RuntimeError(
            "Production requires a non-placeholder JWT_SECRET_KEY "
            "of at least 32 bytes"
        )
    JWT_SECRET_KEY = configured_secret
elif is_placeholder_secret or not configured_secret:
    JWT_SECRET_KEY = secrets.token_urlsafe(48)
    logger.warning(
        "No usable JWT_SECRET_KEY configured; using an ephemeral "
        "development/test key that changes after restart"
    )
elif len(configured_secret.encode("utf-8")) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY must contain at least 32 bytes"
    )
else:
    JWT_SECRET_KEY = configured_secret

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").strip().upper()
if JWT_ALGORITHM != "HS256":
    raise RuntimeError("Only the HS256 JWT algorithm is supported")

try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("JWT_EXPIRE_MINUTES", "1440")
    )
except ValueError as exc:
    raise RuntimeError(
        "JWT_EXPIRE_MINUTES must be an integer"
    ) from exc

if not 1 <= ACCESS_TOKEN_EXPIRE_MINUTES <= 10080:
    raise RuntimeError(
        "JWT_EXPIRE_MINUTES must be between 1 and 10080"
    )


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(
            plain_password,
            password_hash,
        )
    except (TypeError, ValueError) as exc:
        logger.warning("Password verification failed: %s", exc)
        return False


def create_access_token(subject: str, extra_claims: Optional[dict] = None) -> str:
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("Token subject must be a non-empty string")

    claims = extra_claims or {}
    reserved_claims = {
        "sub",
        "exp",
        "iat",
        "nbf",
        "iss",
        "aud",
    }
    if reserved_claims.intersection(claims):
        raise ValueError("Extra claims cannot override reserved JWT claims")

    now = utcnow()
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        **claims,
        "sub": subject,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        if not isinstance(payload.get("sub"), str) or not payload["sub"].strip():
            raise JWTError("Missing token subject")
        if "exp" not in payload:
            raise JWTError("Missing token expiration")
        return payload
    except JWTError as exc:
        logger.warning("Rejected invalid or expired access token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc