"""
Alert Correlation Rules Engine API — Phase 6A.

GET  /api/rules              — list all rules (analyst+)
POST /api/rules              — create rule (admin)
PUT  /api/rules/{id}         — update rule (admin)
DELETE /api/rules/{id}       — delete rule (admin)
POST /api/rules/{id}/toggle  — enable/disable (admin)
POST /api/rules/evaluate     — dry-run against a sample detection (analyst+)

Literal "/evaluate" is declared BEFORE /{id} to avoid path-param capture.
"""
from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import require_admin, require_analyst

router = APIRouter(prefix="/api/rules", tags=["rules"])

try:
    from backend.app.services.rules_service import rules_service
    _svc = rules_service
except Exception as _e:
    _svc = None  # type: ignore[assignment]
    print(f"[RULES] service unavailable: {_e}")


def _svc_or_503():
    if _svc is None:
        raise HTTPException(503, "Rules service unavailable")
    return _svc


# ── Must precede /{id} ───────────────────────────────────────────────────────

@router.post("/evaluate")
def evaluate_rule(_: dict = Depends(require_analyst), body: dict = None):
    """
    Dry-run a detection dict against the rules engine.
    Returns which rule would match and what action it would take.
    """
    if body is None:
        body = {}
    svc = _svc_or_503()
    return svc.evaluate_explain(body)


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("")
def list_rules(_: dict = Depends(require_analyst)):
    svc = _svc_or_503()
    return svc.get_all()


@router.post("")
def create_rule(body: dict, user: dict = Depends(require_admin)):
    svc = _svc_or_503()
    if not body.get("name"):
        raise HTTPException(422, "name is required")
    if body.get("action") not in ("block", "rate_limit", "alert", "escalate"):
        raise HTTPException(422, "action must be block|rate_limit|alert|escalate")
    body["created_by"] = user.get("username", "admin")
    try:
        return svc.add_rule(body)
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.put("/{rule_id}")
def update_rule(rule_id: str, body: dict, _: dict = Depends(require_admin)):
    svc = _svc_or_503()
    if "action" in body and body["action"] not in ("block", "rate_limit", "alert", "escalate"):
        raise HTTPException(422, "action must be block|rate_limit|alert|escalate")
    result = svc.update_rule(rule_id, body)
    if result is None:
        raise HTTPException(404, "Rule not found")
    return result


@router.delete("/{rule_id}")
def delete_rule(rule_id: str, _: dict = Depends(require_admin)):
    svc = _svc_or_503()
    if not svc.delete_rule(rule_id):
        raise HTTPException(404, "Rule not found")
    return {"deleted": True}


@router.post("/{rule_id}/toggle")
def toggle_rule(rule_id: str, _: dict = Depends(require_admin)):
    svc = _svc_or_503()
    rules = svc.get_all()
    rule = next((r for r in rules if r["id"] == rule_id), None)
    if not rule:
        raise HTTPException(404, "Rule not found")
    result = svc.update_rule(rule_id, {"enabled": not rule["enabled"]})
    return result
