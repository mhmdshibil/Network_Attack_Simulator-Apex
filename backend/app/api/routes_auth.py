"""Auth endpoints — Phase 11 + Phase 6B (2FA)."""
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.app.core.auth import (
    authenticate_user, create_access_token, TOKEN_EXPIRE_MINUTES, AUTH_ENABLED, TOTP_ENABLED,
)
from backend.app.services.demo_mode import DEMO_MODE

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 password flow. Returns a Bearer JWT.
    When AUTH_ENABLED=false this still works so the frontend can authenticate
    opportunistically without errors.

    When TOTP_ENABLED=true and the user has 2FA set up, returns:
      {requires_2fa: true, temp_token: "...", role: "..."}
    The frontend must POST to /api/auth/2fa/verify with temp_token + code.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Phase 6B — 2FA gate: only when TOTP_ENABLED=true
    if TOTP_ENABLED:
        try:
            from backend.app.api.routes_2fa import _user_config
            cfg = _user_config(user["username"])
            if cfg and cfg.get("enabled"):
                temp_token = create_access_token(
                    data={"sub": user["username"], "role": user["role"], "type": "2fa_pending"},
                    expires_delta=timedelta(minutes=5),
                )
                return {"requires_2fa": True, "temp_token": temp_token, "role": user["role"]}
        except Exception:
            pass  # 2FA store read failure → fall through to normal login

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
        "totp_enabled": TOTP_ENABLED,
        "llm_configured": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
        "demo_mode": DEMO_MODE,
    }
