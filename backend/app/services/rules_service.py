"""
RulesService — Phase 6A: Alert Correlation Rules Engine.

Admins define priority-ordered rules with condition objects.
On each detection, evaluate() walks enabled rules in priority order and
returns the first matching action (or None). Pure in-memory evaluation —
no I/O on the detection hot path.

Conditions are ANDed together. Supported fields:
  attack_type, confidence, risk_score, source_ip, target_zone, country_code
Supported operators:
  eq, gt, lt, gte, lte, in, not_in, contains
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select as sa_select

_DEFAULT_RULES = [
    {
        "name":        "Block high-confidence bruteforce",
        "description": "Immediately block bruteforce with ≥90% confidence",
        "enabled":     True,
        "conditions":  [
            {"field": "attack_type", "operator": "eq",  "value": "bruteforce"},
            {"field": "confidence",  "operator": "gte", "value": 0.9},
        ],
        "action":      "block",
        "priority":    1,
        "created_by":  "system",
    },
    {
        "name":        "Escalate known-bad countries",
        "description": "Escalate traffic from high-risk country codes",
        "enabled":     True,
        "conditions":  [
            {"field": "country_code", "operator": "in", "value": ["RU", "CN", "KP", "IR"]},
        ],
        "action":      "escalate",
        "priority":    2,
        "created_by":  "system",
    },
    {
        "name":        "Alert on low-confidence detections",
        "description": "Flag low-confidence signals for analyst review",
        "enabled":     True,
        "conditions":  [
            {"field": "confidence", "operator": "lt", "value": 0.6},
        ],
        "action":      "alert",
        "priority":    10,
        "created_by":  "system",
    },
]


def _rule_to_dict(r) -> dict:
    return {
        "id":            r.id,
        "name":          r.name,
        "description":   r.description,
        "enabled":       r.enabled,
        "conditions":    r.conditions or [],
        "action":        r.action,
        "priority":      r.priority,
        "created_by":    r.created_by,
        "created_at":    r.created_at.isoformat() if r.created_at else None,
        "trigger_count": r.trigger_count,
        "last_triggered": r.last_triggered.isoformat() if r.last_triggered else None,
    }


class RulesService:
    def __init__(self):
        # Enabled rules sorted by priority (hot-path cache)
        self._cache: list[dict] = []
        # All rules for API responses
        self._all: list[dict] = []
        self._loaded = False

    # ── Internal async DB helpers ────────────────────────────────────────────

    async def _db_load(self) -> list[dict]:
        from backend.app.models.rules_model import Rule
        from backend.app.core.database import _init_engine
        _, sm = _init_engine()
        async with sm() as s:
            result = await s.execute(sa_select(Rule).order_by(Rule.priority.asc()))
            rules = result.scalars().all()
            if not rules:
                for d in _DEFAULT_RULES:
                    s.add(Rule(id=str(uuid.uuid4()), **d))
                await s.commit()
                result2 = await s.execute(sa_select(Rule).order_by(Rule.priority.asc()))
                rules = result2.scalars().all()
            return [_rule_to_dict(r) for r in rules]

    async def _db_add(self, data: dict) -> dict:
        from backend.app.models.rules_model import Rule
        from backend.app.core.database import _init_engine
        _, sm = _init_engine()
        async with sm() as s:
            rule = Rule(
                id=str(uuid.uuid4()),
                name=data["name"],
                description=data.get("description"),
                enabled=data.get("enabled", True),
                conditions=data.get("conditions", []),
                action=data["action"],
                priority=data.get("priority", 10),
                created_by=data.get("created_by", "admin"),
            )
            s.add(rule)
            await s.commit()
            await s.refresh(rule)
            return _rule_to_dict(rule)

    async def _db_update(self, rule_id: str, data: dict) -> Optional[dict]:
        from backend.app.models.rules_model import Rule
        from backend.app.core.database import _init_engine
        _, sm = _init_engine()
        async with sm() as s:
            result = await s.execute(sa_select(Rule).where(Rule.id == rule_id))
            rule = result.scalar_one_or_none()
            if not rule:
                return None
            for field in ("name", "description", "enabled", "conditions", "action", "priority"):
                if field in data:
                    setattr(rule, field, data[field])
            await s.commit()
            await s.refresh(rule)
            return _rule_to_dict(rule)

    async def _db_delete(self, rule_id: str) -> bool:
        from backend.app.models.rules_model import Rule
        from backend.app.core.database import _init_engine
        _, sm = _init_engine()
        async with sm() as s:
            result = await s.execute(sa_select(Rule).where(Rule.id == rule_id))
            rule = result.scalar_one_or_none()
            if not rule:
                return False
            await s.delete(rule)
            await s.commit()
            return True

    async def _db_increment_trigger(self, rule_id: str) -> None:
        from backend.app.models.rules_model import Rule
        from backend.app.core.database import _init_engine
        _, sm = _init_engine()
        async with sm() as s:
            result = await s.execute(sa_select(Rule).where(Rule.id == rule_id))
            rule = result.scalar_one_or_none()
            if rule:
                rule.trigger_count = (rule.trigger_count or 0) + 1
                rule.last_triggered = datetime.now(timezone.utc)
                await s.commit()

    # ── Public sync API ──────────────────────────────────────────────────────

    def load_rules(self) -> None:
        """Load rules from DB into memory. Call at startup."""
        try:
            from backend.app.core.database import run_async
            rules = run_async(self._db_load(), timeout=10)
            self._all = rules
            self._cache = sorted([r for r in rules if r["enabled"]], key=lambda r: r["priority"])
            self._loaded = True
            print(f"[RULES] loaded {len(self._all)} rule(s) ({len(self._cache)} enabled)")
        except Exception as exc:
            print(f"[RULES] load failed, continuing without rules: {exc}")

    def reload_cache(self) -> None:
        """Reload after any CRUD change. Called from route handlers."""
        self.load_rules()

    def evaluate(self, detection: dict) -> Optional[str]:
        """
        Walk enabled rules in priority order.
        Return first matching action, or None.
        Also fire-and-forget a trigger_count increment.
        """
        for rule in self._cache:
            if self._match(rule["conditions"], detection):
                try:
                    from backend.app.core.database import run_async_bg
                    run_async_bg(self._db_increment_trigger(rule["id"]))
                except Exception:
                    pass
                return rule["action"]
        return None

    def get_all(self) -> list[dict]:
        return list(self._all)

    def add_rule(self, data: dict) -> dict:
        from backend.app.core.database import run_async
        rule = run_async(self._db_add(data), timeout=10)
        self.reload_cache()
        return rule

    def update_rule(self, rule_id: str, data: dict) -> Optional[dict]:
        from backend.app.core.database import run_async
        rule = run_async(self._db_update(rule_id, data), timeout=10)
        if rule:
            self.reload_cache()
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        from backend.app.core.database import run_async
        ok = run_async(self._db_delete(rule_id), timeout=10)
        if ok:
            self.reload_cache()
        return ok

    # ── Condition evaluation ─────────────────────────────────────────────────

    def _match(self, conditions: list, detection: dict) -> bool:
        for cond in conditions:
            if not self._eval_condition(cond, detection):
                return False
        return bool(conditions)   # empty conditions list never matches

    def _eval_condition(self, cond: dict, detection: dict) -> bool:
        field    = cond.get("field", "")
        op       = cond.get("operator", "eq")
        expected = cond.get("value")

        # Field resolution with aliases
        if field == "attack_type":
            actual = detection.get("label")
        elif field == "source_ip":
            actual = detection.get("ip")
        elif field == "country_code":
            actual = (detection.get("geo") or {}).get("country_code")
        else:
            actual = detection.get(field)

        if actual is None:
            return False

        try:
            if op == "eq":       return actual == expected
            if op == "gt":       return float(actual) > float(expected)
            if op == "lt":       return float(actual) < float(expected)
            if op == "gte":      return float(actual) >= float(expected)
            if op == "lte":      return float(actual) <= float(expected)
            if op == "in":       return actual in (expected or [])
            if op == "not_in":   return actual not in (expected or [])
            if op == "contains": return str(expected) in str(actual)
        except (TypeError, ValueError):
            return False
        return False

    # ── Dry-run helper ───────────────────────────────────────────────────────

    def evaluate_explain(self, detection: dict) -> dict:
        """Return matched rule + action for /api/rules/evaluate."""
        for rule in self._cache:
            if self._match(rule["conditions"], detection):
                return {"matched": True, "rule_id": rule["id"], "rule_name": rule["name"],
                        "action": rule["action"], "priority": rule["priority"]}
        return {"matched": False, "rule_id": None, "rule_name": None, "action": None}


# Module-level singleton — loaded at app startup
rules_service = RulesService()
