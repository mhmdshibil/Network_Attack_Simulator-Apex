# backend/app/response/engine.py
# This module serves as the unified integration engine that orchestrates the entire end-to-end
# response process. It connects the various stages of the analytics and response pipeline, from
# initial data correlation to final action execution. The `evaluate_and_respond` function is the
# central entry point, coordinating the flow of data between the correlation, risk, confidence,
# decision, and action modules. This streamlined workflow ensures that a potential threat can be
# analyzed and acted upon in a seamless and automated fashion.
from backend.app.analytics.explainability import build_explanation
from backend.app.analytics.correlation import correlate_attacks
from backend.app.analytics.risk import compute_risk
from backend.app.analytics.confidence import compute_confidence
from backend.app.response.decision import decide_action
from backend.app.response.actions import execute_action


def evaluate_and_respond(ip: str, window: str):
    """
    Orchestrates the end-to-end evaluation and response process for a given IP address.

    This function serves as the high-level coordinator for the response engine. It follows a
    sequential pipeline to process threat data and determine an appropriate action:
    1.  Correlate Attacks: Gathers and correlates all attack events related to the specified IP
        within the given time window.
    2.  Compute Risk: Calculates a risk score and severity level based on the correlated events.
    3.  Compute Confidence: Determines the confidence level of the threat assessment.
    4.  Decide Action: Translates the risk and confidence scores into a clear decision.
    5.  Execute Action: Simulates the execution of the decided action.

    Args:
        ip (str): The IP address to be evaluated.
        window (str): The time window to consider for the analysis (e.g., "5m", "1h").

    Returns:
        dict: A comprehensive dictionary containing the results from each stage of the pipeline,
              including the final risk score, confidence, decision, and action result.
    """

    correlations = correlate_attacks(window=window)
    correlations = [c for c in correlations if c.get("ip") == ip]

    risks = compute_risk(correlations, window)
    risk = risks[0] if risks else {
        "risk_score": 0,
        "severity": "low"
    }

    confidence_result = compute_confidence(correlations, window)

    decision_payload = decide_action(
        ip=ip,
        risk_score=risk["risk_score"],
        confidence=confidence_result.get("score", 0.0)
    )

    action_result = execute_action(decision_payload)

    explanation = build_explanation(
        ip=ip,
        decision=decision_payload["decision"],
        risk_score=risk["risk_score"],
        confidence=confidence_result.get("score", 0.0),
        signals={
            "attack_count": len(correlations),
            "severity": decision_payload.get("severity", risk.get("severity", "low")),
            "window": window
        }
    )

    explanation["decision"] = decision_payload["decision"]
    explanation["action"] = action_result.get("action", decision_payload["decision"])

    return explanation