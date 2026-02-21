from fastapi import APIRouter
from pathlib import Path
import json

router = APIRouter(prefix="/api/audit", tags=["audit"])

AUDIT_FILE = Path("data/audit/security_events.jsonl")


@router.get("/events")
def get_events(limit: int = 50):
    if not AUDIT_FILE.exists():
        return {"events": []}

    with AUDIT_FILE.open() as f:
        lines = f.readlines()[-limit:]

    events = [json.loads(line) for line in lines]
    return {"events": events}


@router.get("/ip/{ip}")
def get_events_by_ip(ip: str, limit: int = 50):
    if not AUDIT_FILE.exists():
        return {"events": []}

    results = []

    with AUDIT_FILE.open() as f:
        for line in f:
            event = json.loads(line)
            if event["ip"] == ip:
                results.append(event)

    return {"events": results[-limit:]}