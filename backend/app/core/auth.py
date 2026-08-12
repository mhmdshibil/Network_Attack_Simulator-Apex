"""
JWT authentication — Phase 11.

Controlled by AUTH_ENABLED env var (default: false).
When disabled, require_analyst / require_admin are no-ops so the
existing dashboard continues to work without any credential setup.

Default credentials (change via env or extend _USERS dict):
  admin / adminpass   → admin role
  analyst / analystpass → analyst role
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "false").lower() == "true"
_SECRET_KEY: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production-apex")
_ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

_USERS: dict[str, dict] = {
    "admin": {
        "username": "admin",
        "hashed_password": _pwd.hash(os.getenv("ADMIN_PASSWORD", "adminpass")),
        "role": "admin",
    },
    "analyst": {
        "username": "analyst",
        "hashed_password": _pwd.hash(os.getenv("ANALYST_PASSWORD", "analystpass")),
        "role": "analyst",
    },
}

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = _USERS.get(username)
    if not user or not _pwd.verify(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, _SECRET_KEY, algorithm=_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _anon_analyst() -> dict:
    return {"username": "anonymous", "role": "analyst"}


def _anon_admin() -> dict:
    return {"username": "anonymous", "role": "admin"}


def require_analyst(token: Optional[str] = Depends(_oauth2_scheme)) -> dict:
    """FastAPI dependency — requires analyst or admin role when AUTH_ENABLED=true."""
    if not AUTH_ENABLED:
        return _anon_analyst()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(token)
    if payload.get("role") not in ("analyst", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Analyst role required")
    return payload


def require_admin(token: Optional[str] = Depends(_oauth2_scheme)) -> dict:
    """FastAPI dependency — requires admin role when AUTH_ENABLED=true."""
    if not AUTH_ENABLED:
        return _anon_admin()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(token)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return payload


def ws_require_analyst(token: Optional[str] = Query(default=None)) -> dict:
    """
    WebSocket dependency — reads token from query param `?token=<jwt>`.
    WebSocket clients cannot send Authorization headers, so we use a
    short-lived token passed as a query parameter instead.
    """
    if not AUTH_ENABLED:
        return _anon_analyst()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="WS token required")
    payload = _decode_token(token)
    if payload.get("role") not in ("analyst", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Analyst role required")
    return payload
