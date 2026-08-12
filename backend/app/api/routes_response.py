from fastapi import APIRouter, Depends, HTTPException
from fastapi import status

from backend.app.schemas.respond import RespondRequest
from backend.app.analytics.correlation import correlate_attacks
from backend.app.analytics.risk import compute_risk
from backend.app.response.engine import evaluate_and_respond
from backend.app.core.auth import require_admin

router = APIRouter(
    prefix="/api/respond",
    tags=["response"]
)


@router.post("/", status_code=status.HTTP_200_OK)
def respond(req: RespondRequest, _: dict = Depends(require_admin)):
    """
    Phase 8/9 – Autonomous Response Engine (Hardened)

    Flow:
    correlate → risk → decision → action

    Safety features:
    • Handles empty analytics safely
    • Prevents KeyErrors
    • Guards against malformed risk objects
    • Never crashes the API
    """

    try:
        correlations = correlate_attacks(window=req.window)

        if not correlations:
            return {
                "ip": req.ip,
                "decision": "MONITOR",
                "action": "noop",
                "executed": False,
                "reason": "No recent attack correlations"
            }

        risk_results = compute_risk(correlations, req.window)

        if not isinstance(risk_results, list):
            raise HTTPException(
                status_code=500,
                detail="Risk engine returned invalid format"
            )

        ip_risk = next(
            (r for r in risk_results if r.get("ip") == req.ip),
            None
        )

        if not ip_risk:
            return {
                "ip": req.ip,
                "decision": "MONITOR",
                "action": "noop",
                "executed": False,
                "reason": "No analytics found for IP"
            }

        # 🔒 Defensive extraction (never trust upstream data)
        details = ip_risk.get("details") or []
        if not isinstance(details, list):
            details = []

        attack_count = sum(d.get("count", 1) for d in details)

        risk_score = float(ip_risk.get("risk_score", 0.0))
        confidence = float(ip_risk.get("confidence", 0.0))
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

    except HTTPException:
        raise

    except Exception as e:
        # Last‑resort safety net (production‑grade behavior)
        return {
            "ip": req.ip,
            "decision": "MONITOR",
            "action": "noop",
            "executed": False,
            "reason": "Response engine fallback",
            "error": str(e)
        }