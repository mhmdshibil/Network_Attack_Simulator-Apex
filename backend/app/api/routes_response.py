from fastapi import APIRouter, HTTPException

from backend.app.schemas.respond import RespondRequest
from backend.app.analytics.correlation import correlate_attacks
from backend.app.analytics.risk import compute_risk
from backend.app.response.engine import evaluate_and_respond

router = APIRouter(
    prefix="/api/respond",
    tags=["response"]
)


@router.post("/")
def respond(req: RespondRequest):
    """
    Phase 8 – Autonomous Response Engine

    Flow:
    correlate → risk → decision → action
    """

    correlations = correlate_attacks(window=req.window)

    if not correlations:
        return {
            "ip": req.ip,
            "decision": "MONITOR",
            "action": "monitor",
            "executed": False,
            "reason": "No recent attack correlations"
        }

    risk_results = compute_risk(correlations, req.window)

    ip_risk = next((r for r in risk_results if r["ip"] == req.ip), None)

    if not ip_risk:
        return {
            "ip": req.ip,
            "decision": "MONITOR",
            "action": "monitor",
            "executed": False,
            "reason": "No analytics found for IP"
        }

    # 🔒 Defensive defaults (prevents KeyError forever)
    details = ip_risk.get("details", [])
    attack_count = sum(d.get("count", 1) for d in details)
    risk_score = ip_risk.get("risk_score", 0.0)
    confidence = ip_risk.get("confidence", 0.0)
    severity = ip_risk.get("severity", "low")

    response = evaluate_and_respond(
        ip=req.ip,
        risk_score=risk_score,
        confidence=confidence,
        severity=severity,
        attack_count=attack_count,
        window=req.window
    )

    return response