import json
from datetime import datetime, timezone

from backend.app.core.paths import HARD_BLOCKED_IPS_FILE


def _load() -> dict:
    if not HARD_BLOCKED_IPS_FILE.exists():
        return {}
    try:
        return json.loads(HARD_BLOCKED_IPS_FILE.read_text())
    except Exception:
        return {}


def _save(data: dict):
    HARD_BLOCKED_IPS_FILE.parent.mkdir(parents=True, exist_ok=True)
    HARD_BLOCKED_IPS_FILE.write_text(json.dumps(data, indent=2))


def is_hard_blocked(ip: str) -> bool:
    data = _load()
    return ip in data


def add_hard_block(ip: str, reason: str):
    data = _load()
    data[ip] = {
        "reason": reason,
        "blocked_at": datetime.now(timezone.utc).isoformat()
    }
    _save(data)