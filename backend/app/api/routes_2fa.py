"""
Two-Factor Authentication (TOTP) API — Phase 6B.

POST /api/auth/2fa/setup     — generate secret + QR code (JWT required)
POST /api/auth/2fa/activate  — confirm scan; store secret (JWT + TOTP code)
POST /api/auth/2fa/verify    — exchange temp_token + code for full JWT
POST /api/auth/2fa/disable   — remove 2FA from user (JWT + TOTP code)
GET  /api/auth/2fa/status    — current 2FA state for authenticated user

Transparent when TOTP_ENABLED=false (status returns enabled=false, other
endpoints are no-ops that return graceful errors).
"""
import base64
import io
import json
import os
import secrets
from datetime import timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import require_analyst, create_access_token, _decode_token, _SECRET_KEY, _ALGORITHM
from backend.app.core.paths import BASE_DIR

TOTP_ENABLED: bool = os.getenv("TOTP_ENABLED", "false").lower() == "true"
_2FA_FILE = BASE_DIR / "data" / "policies" / "user_2fa.json"

router = APIRouter(prefix="/api/auth/2fa", tags=["2fa"])


# ── Storage helpers ───────────────────────────────────────────────────────────

def _load_store() -> dict:
    if _2FA_FILE.exists():
        try:
            return json.loads(_2FA_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_store(data: dict) -> None:
    _2FA_FILE.parent.mkdir(parents=True, exist_ok=True)
    _2FA_FILE.write_text(json.dumps(data, indent=2))


def _user_config(username: str) -> Optional[dict]:
    return _load_store().get(username)


# ── QR code helper ────────────────────────────────────────────────────────────

def _make_qr_base64(uri: str) -> str:
    """Render the TOTP provisioning URI as a base64 PNG."""
    try:
        import qrcode
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        # qrcode not installed — return the raw URI encoded so the frontend
        # can fall back to showing the text
        return base64.b64encode(uri.encode()).decode()


# ── Backup codes ──────────────────────────────────────────────────────────────

def _gen_backup_codes(n: int = 8) -> list[str]:
    return [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(n)]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
def status(user: dict = Depends(require_analyst)):
    cfg = _user_config(user["username"])
    return {
        "totp_enabled_globally": TOTP_ENABLED,
        "enabled": bool(cfg and cfg.get("enabled")),
        "setup_complete": bool(cfg and cfg.get("secret")),
    }


@router.post("/setup")
def setup(user: dict = Depends(require_analyst)):
    """Generate a new TOTP secret + QR code. Does NOT activate 2FA yet."""
    try:
        import pyotp
    except ImportError:
        raise HTTPException(501, "pyotp not installed — run: pip install pyotp qrcode[pil]")

    secret = pyotp.random_base32()
    username = user["username"]
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=username, issuer_name="Apex Argus SOC"
    )
    qr_b64 = _make_qr_base64(uri)
    backup_codes = _gen_backup_codes()

    # Persist the pending secret (not yet enabled)
    store = _load_store()
    existing = store.get(username, {})
    store[username] = {**existing, "pending_secret": secret, "backup_codes": backup_codes}
    _save_store(store)

    return {"secret": secret, "qr_code_base64": qr_b64, "backup_codes": backup_codes, "uri": uri}


@router.post("/activate")
def activate(body: dict, user: dict = Depends(require_analyst)):
    """Confirm the user scanned correctly; activate 2FA."""
    try:
        import pyotp
    except ImportError:
        raise HTTPException(501, "pyotp not installed")

    code = str(body.get("code", "")).strip()
    username = user["username"]
    store = _load_store()
    cfg = store.get(username, {})
    secret = cfg.get("pending_secret")
    if not secret:
        raise HTTPException(400, "No pending 2FA setup — call /setup first")

    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(401, "Invalid TOTP code")

    store[username] = {
        "secret":       secret,
        "enabled":      True,
        "backup_codes": cfg.get("backup_codes", []),
    }
    _save_store(store)
    return {"enabled": True}


@router.post("/verify")
def verify(body: dict):
    """
    Exchange a 2fa_pending temp_token + TOTP code for a full JWT.
    Called by the frontend when the user enters their 6-digit code.
    """
    try:
        import pyotp
    except ImportError:
        raise HTTPException(501, "pyotp not installed")

    temp_token = body.get("temp_token", "")
    code       = str(body.get("code", "")).strip()

    if not temp_token or not code:
        raise HTTPException(422, "temp_token and code are required")

    try:
        payload = _decode_token(temp_token)
    except HTTPException:
        raise HTTPException(401, "Invalid or expired temp_token")

    if payload.get("type") != "2fa_pending":
        raise HTTPException(401, "Not a 2FA pending token")

    username = payload.get("sub")
    cfg = _user_config(username)
    if not cfg or not cfg.get("secret"):
        raise HTTPException(400, "2FA not configured for this user")

    totp = pyotp.TOTP(cfg["secret"])
    backup_codes = cfg.get("backup_codes", [])

    if not totp.verify(code, valid_window=1):
        # Check backup codes
        norm = code.replace(" ", "").replace("-", "")
        matched_backup = next((c for c in backup_codes if c.replace("-", "") == norm), None)
        if not matched_backup:
            raise HTTPException(401, "Invalid TOTP code")
        # Consume the backup code
        store = _load_store()
        store[username]["backup_codes"] = [c for c in backup_codes if c != matched_backup]
        _save_store(store)

    # Issue full JWT with the user's role from the temp token
    access_token = create_access_token(
        data={"sub": username, "role": payload.get("role", "analyst")},
        expires_delta=timedelta(minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "60"))),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/disable")
def disable(body: dict, user: dict = Depends(require_analyst)):
    """Remove 2FA for the current user (requires a valid TOTP code)."""
    try:
        import pyotp
    except ImportError:
        raise HTTPException(501, "pyotp not installed")

    code = str(body.get("code", "")).strip()
    username = user["username"]
    cfg = _user_config(username)

    if not cfg or not cfg.get("enabled"):
        raise HTTPException(400, "2FA is not enabled for this user")

    totp = pyotp.TOTP(cfg["secret"])
    if not totp.verify(code, valid_window=1):
        raise HTTPException(401, "Invalid TOTP code")

    store = _load_store()
    store.pop(username, None)
    _save_store(store)
    return {"disabled": True}
