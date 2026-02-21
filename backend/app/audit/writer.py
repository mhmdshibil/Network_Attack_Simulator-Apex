# backend/app/audit/writer.py

import json
from pathlib import Path

AUDIT_FILE = Path("data/audit/security_events.jsonl")


def write_audit_event(event: dict) -> None:
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")