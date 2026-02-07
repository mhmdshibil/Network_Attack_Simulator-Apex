# backend/app/response/engine.py

from datetime import datetime
import csv
from pathlib import Path

from backend.app.analytics.explainability import build_explanation
from backend.app.analytics.correlation import correlate_attacks
from backend.app.analytics.risk import compute_risk
from backend.app.analytics.confidence import compute_confidence
from backend.app.response.decision import decide_action
from backend.app.response.actions import execute_action


AUDIT_FILE = Path("data/audit/decision_audit.csv")


def log_audit_event(
    ip: str,
    window: str,
    risk_score: float,
    confidence: float,
    decision: str,
    action: str,
    source: str
):
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(AUDIT_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.utcnow().isoformat(),
            ip,
            window,
            risk_score,
            confidence,
            decision,
            action,
            source
        ])


def evaluate_and_respond(ip: str, window: str):
    correlations = correlate_attacks(window=window)
    correlations = [c for c in correlations if c.get("ip") == ip]

    risks = compute_risk(correlations, window)
    risk = risks[0] if risks else {
        "risk_score": 0,
        "severity": "low"
    }

    confidence_result = compute_confidence(correlations, window)

    attack_count = len(correlations)

    decision_payload = decide_action(
        ip=ip,
        attack_count=attack_count,
        risk_score=risk["risk_score"],
        confidence=confidence_result.get("score", 0.0)
    )

    action_result = execute_action(decision_payload)

    source = "policy"

    log_audit_event(
        ip=ip,
        window=window,
        risk_score=risk["risk_score"],
        confidence=confidence_result.get("score", 0.0),
        decision=decision_payload["decision"],
        action=action_result.get("action", decision_payload["decision"]),
        source=source
    )

    explanation = build_explanation(
        ip=ip,
        decision=decision_payload["decision"],
        risk_score=risk["risk_score"],
        confidence=confidence_result.get("score", 0.0),
        signals={
            "attack_count": attack_count,
            "severity": decision_payload["severity"],
            "window": window
        }
    )

    explanation["decision"] = decision_payload["decision"]
    explanation["action"] = action_result.get("action", decision_payload["decision"])

    return explanation