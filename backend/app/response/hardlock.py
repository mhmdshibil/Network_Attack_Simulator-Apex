import json
from pathlib import Path
from datetime import datetime, timezone

HARDLOCK_FILE = Path("data/processed/hard_blocked_ips.json")


def _load() -> dict:
    if not HARDLOCK_FILE.exists():
        return {}
    try:
        return json.loads(HARDLOCK_FILE.read_text())
    except Exception:
        return {}


def _save(data: dict):
    HARDLOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    HARDLOCK_FILE.write_text(json.dumps(data, indent=2))


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