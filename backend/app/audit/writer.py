# backend/app/audit/writer.py

import json
from pathlib import Path
from typing import Dict

AUDIT_FILE = Path("data/audit/security_events.jsonl")


def write_audit_event(event: Dict):
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_FILE.open("a") as f:
        f.write(json.dumps(event) + "\n")