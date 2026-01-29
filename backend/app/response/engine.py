from backend.app.analytics.correlation import correlate_attacks
from backend.app.analytics.risk import compute_risk
from backend.app.analytics.policy import evaluate_policy
from backend.app.response.actions import execute_actions


def evaluate_and_respond(ip: str, window: str):
    context = _build_context(ip, window)
    decision = _apply_policy(context)
    actions_result = _execute_actions(ip, decision)

    return {
        "ip": ip,
        "window": window,
        "risk": context["risk"]["severity"],
        "risk_score": context["risk"]["risk_score"],
        "decision": decision.get("decision"),
        "actions": actions_result,
        "confidence": context["risk"].get("confidence", 1.0)
    }


def _build_context(ip: str, window: str):
    correlations = correlate_attacks(window=window)
    correlations = [c for c in correlations if c.get("ip") == ip]

    risks = compute_risk(correlations)
    risk = risks[0] if risks else {
        "risk_score": 0,
        "severity": "low",
        "details": []
    }

    return {
        "ip": ip,
        "window": window,
        "correlations": correlations,
        "risk": risk
    }


def _apply_policy(context: dict):
    return evaluate_policy(
        ip=context["ip"],
        risk=context["risk"],
        correlations=context["correlations"]
    )


def _execute_actions(ip: str, decision: dict):
    actions = decision.get("actions", [])
    if not actions:
        return []

    return execute_actions(
        ip=ip,
        actions=actions,
        reason=decision.get("reason", "")
    )