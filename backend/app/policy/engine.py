import json
from pathlib import Path
from datetime import datetime, timedelta

POLICY_FILE = Path("data/policies/policies.json")
BLOCK_LOG = Path("data/processed/blocked_ips.log")


def load_policies():
    if not POLICY_FILE.exists():
        return {}
    return json.loads(POLICY_FILE.read_text())


def recently_blocked(ip: str, cooldown_minutes: int) -> bool:
    if not BLOCK_LOG.exists():
        return False

    now = datetime.utcnow()
    with open(BLOCK_LOG) as f:
        for line in f:
            logged_ip, ts = line.strip().split(",")
            if logged_ip == ip:
                if now - datetime.fromisoformat(ts) < timedelta(minutes=cooldown_minutes):
                    return True
    return False


def enforce_policy(ip: str, ai_decision: dict, signals: dict):
    policies = load_policies()

    # 1. Allowlist → absolute allow
    if ip in policies.get("allowlist", []):
        return {
            "decision": "ALLOW",
            "policy_applied": "allowlist_override"
        }

    # 2. Blocklist → absolute block
    if ip in policies.get("blocklist", []):
        return {
            "decision": "BLOCK",
            "policy_applied": "blocklist_override"
        }

    # 3. Always-block attack types
    attack_type = signals.get("attack_type")
    if attack_type in policies.get("rules", {}).get("always_block_attacks", []):
        return {
            "decision": "BLOCK",
            "policy_applied": "attack_type_override"
        }

    # 4. Cooldown enforcement
    cooldown = policies.get("rules", {}).get("cooldown_minutes", 0)
    if recently_blocked(ip, cooldown):
        return {
            "decision": "BLOCK",
            "policy_applied": "cooldown_enforced"
        }

    # 5. No policy → AI decision stands
    return ai_decision