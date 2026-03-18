from pathlib import Path
import csv
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[3]
AUDIT_FILE = BASE_DIR / "data/audit/decision_audit.csv"


def log_decision(ip, decision, severity, risk_score, confidence, reason):

    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

    file_exists = AUDIT_FILE.exists()

    with open(AUDIT_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "ip",
                "decision",
                "severity",
                "risk_score",
                "confidence",
                "reason"
            ])

        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            ip,
            decision,
            severity,
            risk_score,
            confidence,
            reason
        ])