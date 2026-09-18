import csv
import json
from pathlib import Path

from backend.app.core.paths import AUDIT_EVENTS_FILE, DECISION_AUDIT_FILE

# Optional DB sink (Phase 2). Guarded so audit logging still works without the
# DB deps installed — JSONL/CSV remain the fallback.
try:
    from backend.app.core import database as _db
except Exception:  # pragma: no cover
    _db = None

_DECISION_AUDIT_FIELDS = [
    "timestamp", "ip", "decision", "severity",
    "risk_score", "confidence", "reason", "attack_count",
]


def write_audit_event(event: dict) -> None:
    AUDIT_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Full structured record → JSONL (primary/fallback)
    with AUDIT_EVENTS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    # Slim decision record → CSV (consumed by routes_system.py)
    write_header = not DECISION_AUDIT_FILE.exists()
    with DECISION_AUDIT_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_DECISION_AUDIT_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(event)

    # Dual-write to DB (non-blocking, guarded — JSONL is the fallback)
    if _db is not None:
        _db.save_audit_event_safe(event)
