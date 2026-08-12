from fastapi import APIRouter, Depends
import pandas as pd
from backend.app.core.paths import DETECTIONS_FILE
from backend.app.ml.mitre_mapping import get_mitre
from backend.app.core.auth import require_analyst

router = APIRouter(prefix="/api", tags=["alerts"])

_LABEL_DISPLAY = {
    "port_scan":     "port scan",
    "sql_injection": "SQL injection",
    "ddos":          "DDoS",
    "bruteforce":    "brute force",
    "malware":       "malware",
}

def _format_alert(row: dict, idx: int) -> dict:
    label = row.get("label", "unknown")
    action = row.get("action", "monitored")
    ip = row.get("ip", "unknown")
    label_nice = _LABEL_DISPLAY.get(label, label.replace("_", " "))

    if action == "blocked":
        message = f"Blocked {label_nice} attempt from {ip}"
        severity = "high"
        action_tag = "BLOCK"
    elif action == "rate_limited":
        message = f"Rate-limited {label_nice} attempt from {ip}"
        severity = "medium"
        action_tag = "RATE-LIMIT"
    else:
        message = f"Monitoring {label_nice} activity from {ip}"
        severity = "medium"
        action_tag = "MONITOR"

    mitre = get_mitre(label)
    return {
        "id": idx,
        "timestamp": row.get("timestamp", ""),
        "message": message,
        "severity": severity,
        "ip": ip,
        "action": action_tag,
        "label": label,
        "mitre_id": mitre["technique_id"],
        "mitre_technique": mitre["technique"],
        "mitre_tactic": mitre["tactic"],
    }


@router.get("/alerts")
def get_alerts(limit: int = 20, _: dict = Depends(require_analyst)):
    if not DETECTIONS_FILE.exists():
        return []

    try:
        df = pd.read_csv(
            DETECTIONS_FILE,
            usecols=["ip", "timestamp", "label", "action"],
        )
        required = {"ip", "timestamp", "label", "action"}
        if not required.issubset(df.columns):
            return []
    except Exception:
        return []

    if df.empty:
        return []

    recent = df.tail(limit).iloc[::-1].reset_index(drop=True)
    return [_format_alert(row, i) for i, row in enumerate(recent.to_dict("records"))]
