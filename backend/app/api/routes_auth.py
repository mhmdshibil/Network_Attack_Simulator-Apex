"""Auth endpoints — Phase 11."""
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.app.core.auth import authenticate_user, create_access_token, TOKEN_EXPIRE_MINUTES, AUTH_ENABLED

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 password flow. Returns a Bearer JWT.
    When AUTH_ENABLED=false this still works so the frontend can authenticate
    opportunistically without errors.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        {"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "expires_in": TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/status")
def auth_status():
    """Returns server feature flags. Public endpoint — no auth required."""
    return {
        "auth_enabled": AUTH_ENABLED,
        "llm_configured": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
    }
