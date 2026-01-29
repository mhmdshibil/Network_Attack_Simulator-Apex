# engine.py
# This file contains the main logic for the response engine.

from backend.app.analytics.correlation import correlate_attacks
from backend.app.analytics.risk import compute_risk
from backend.app.analytics.policy import evaluate_policy
from backend.app.response.actions import execute_actions


def evaluate_and_respond(ip: str, window: str):
    """
    The main function of the response engine. It evaluates the risk and
    determines the appropriate response for a given IP address.
    """
    # Build the context for the evaluation.
    context = _build_context(ip, window)
    # Apply the policy to the context to get a decision.
    decision = _apply_policy(context)
    # Execute the actions based on the decision.
    actions_result = _execute_actions(ip, decision)

    # Return a summary of the evaluation and response.
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
    """
    Build the context for the evaluation by correlating attacks and computing risk.
    """
    # Correlate attacks within the specified window and filter by IP.
    correlations = correlate_attacks(window=window)
    correlations = [c for c in correlations if c.get("ip") == ip]

    # Compute the risk based on the correlations.
    risks = compute_risk(correlations)
    # Get the risk for the IP, or a default low-risk value if not found.
    risk = risks[0] if risks else {
        "risk_score": 0,
        "severity": "low",
        "details": []
    }

    # Return the context dictionary.
    return {
        "ip": ip,
        "window": window,
        "correlations": correlations,
        "risk": risk
    }


def _apply_policy(context: dict):
    """
    Apply the policy to the given context to get a decision.
    """
    # Call the evaluate_policy function with the context information.
    return evaluate_policy(
        ip=context["ip"],
        risk=context["risk"],
        correlations=context["correlations"]
    )


def _execute_actions(ip: str, decision: dict):
    """
    Execute the actions specified in the decision.
    """
    # Get the list of actions from the decision dictionary.
    actions = decision.get("actions", [])
    # If there are no actions, return an empty list.
    if not actions:
        return []

    # Execute the actions and return the results.
    return execute_actions(
        ip=ip,
        actions=actions,
        reason=decision.get("reason", "")
    )