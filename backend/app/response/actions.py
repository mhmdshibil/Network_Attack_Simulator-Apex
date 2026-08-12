"""
Phase 4 enforcement layer — DRY-RUN mode active.

Set environment variable ENFORCE_MODE=live (and confirm you are inside a
sandboxed VM) before real iptables/pfctl calls are enabled.  Until then,
every action is simulated: the decision and audit trail are real, but no
OS-level rule is applied.
"""
import os
import subprocess
import platform
from datetime import datetime, timezone
from typing import Dict

# Set ENFORCE_MODE=live in the environment only inside an isolated sandbox VM.
_DRY_RUN = os.getenv("ENFORCE_MODE", "dry").lower() != "live"


def execute_action(
    *,
    ip: str,
    action: str,
    severity: str,
    risk_score: float,
) -> Dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    mode_tag = "[DRY-RUN]" if _DRY_RUN else "[LIVE]"

    if action == "firewall_block":
        if not _DRY_RUN:
            _apply_block(ip)
        return {
            "executed": not _DRY_RUN,
            "dry_run": _DRY_RUN,
            "action": "firewall_block",
            "ip": ip,
            "severity": severity,
            "risk_score": risk_score,
            "message": f"{mode_tag} IP blocked via firewall rule",
            "timestamp": timestamp,
        }

    if action == "throttle":
        if not _DRY_RUN:
            _apply_throttle(ip)
        return {
            "executed": not _DRY_RUN,
            "dry_run": _DRY_RUN,
            "action": "throttle",
            "ip": ip,
            "severity": severity,
            "risk_score": risk_score,
            "message": f"{mode_tag} Traffic rate-limited",
            "timestamp": timestamp,
        }

    if action == "log":
        return {
            "executed": True,
            "dry_run": False,
            "action": "log",
            "ip": ip,
            "severity": severity,
            "risk_score": risk_score,
            "message": "Event logged for monitoring",
            "timestamp": timestamp,
        }

    return {
        "executed": False,
        "dry_run": _DRY_RUN,
        "action": "noop",
        "ip": ip,
        "severity": severity,
        "risk_score": risk_score,
        "message": "No enforcement action taken",
        "timestamp": timestamp,
    }


def remove_block(ip: str) -> bool:
    """Remove an expired firewall block rule. No-op in dry-run mode."""
    if _DRY_RUN:
        print(f"[DRY-RUN] Would remove block rule for {ip}")
        return False
    return _remove_block(ip)


# ── Private helpers (real enforcement — only reachable when ENFORCE_MODE=live) ──

def _apply_block(ip: str):
    """Add a DROP rule for the IP. Requires sandbox with NET_ADMIN capability."""
    system = platform.system()
    if system == "Linux":
        subprocess.run(["iptables", "-I", "INPUT", "-s", ip, "-j", "DROP"],
                       check=True, timeout=5)
    elif system == "Darwin":
        # pfctl — append to anchors file; reload anchor
        subprocess.run(["pfctl", "-t", "blocked", "-T", "add", ip],
                       check=True, timeout=5)
    else:
        raise RuntimeError(f"Unsupported OS for enforcement: {system}")


def _apply_throttle(ip: str):
    """Rate-limit the IP. Linux tc / nftables — only in sandbox."""
    system = platform.system()
    if system == "Linux":
        subprocess.run(
            ["nft", "add", "rule", "inet", "filter", "input",
             "ip", "saddr", ip, "limit", "rate", "10/second", "accept"],
            check=True, timeout=5,
        )
    else:
        print(f"[WARN] Throttle not implemented for {system} — logged only")


def _remove_block(ip: str) -> bool:
    system = platform.system()
    try:
        if system == "Linux":
            subprocess.run(["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"],
                           check=True, timeout=5)
        elif system == "Darwin":
            subprocess.run(["pfctl", "-t", "blocked", "-T", "delete", ip],
                           check=True, timeout=5)
        return True
    except subprocess.CalledProcessError:
        return False
