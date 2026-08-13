"""
Demo / showcase mode — Phase 16.

When DEMO_MODE=true the scheduler fires one attack every
DEMO_INTERVAL_SECONDS (clamped 120–300s), cycling through all five
attack classes in a shuffled rotation so no class repeats until every
class has had a turn.

When DEMO_MODE=false this module is still importable (routes and status
endpoints work) but the async loop is never started — zero effect on the
existing fast background auto-attack loop.

Every attack — scheduled or manually triggered — goes through the exact
same DetectionEngine / MITRE / SHAP / WebSocket pipeline as normal traffic.
"""
import asyncio
import csv
import ipaddress
import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from backend.app.core.paths import BASE_DIR

# ── Env vars ─────────────────────────────────────────────────────────────────
DEMO_MODE: bool = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_INTERVAL_SECONDS: int = max(
    120, min(300, int(os.getenv("DEMO_INTERVAL_SECONDS", "150")))
)

# ── Constants ─────────────────────────────────────────────────────────────────
ATTACK_CLASSES = ["port_scan", "ddos", "bruteforce", "sql_injection", "malware"]

_RAW_DIR = BASE_DIR / "data" / "raw"
_DEMO_FILE = _RAW_DIR / "demo_attack.csv"

_TRAFFIC_HEADER = [
    "timestamp", "source_ip", "destination_ip", "destination_port",
    "protocol", "packet_count", "request_rate", "success_flag", "label",
]

# ── Private / reserved ranges (RFC 1918, loopback, link-local, CGNAT, etc.) ──
_RESERVED = [
    ipaddress.IPv4Network("0.0.0.0/8"),
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("100.64.0.0/10"),
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv4Network("169.254.0.0/16"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.0.0.0/24"),
    ipaddress.IPv4Network("192.168.0.0/16"),
    ipaddress.IPv4Network("198.18.0.0/15"),
    ipaddress.IPv4Network("224.0.0.0/4"),
    ipaddress.IPv4Network("240.0.0.0/4"),
    ipaddress.IPv4Network("255.255.255.255/32"),
]


def random_public_ip() -> str:
    """Return a random globally-routable IPv4 address, never a private/reserved one."""
    while True:
        addr = ipaddress.IPv4Address(random.randint(1, 2**32 - 2))
        if not any(addr in net for net in _RESERVED):
            return str(addr)


# ── Shuffled rotation ─────────────────────────────────────────────────────────
_deck: list[str] = []


def _next_class() -> str:
    """Pop from the shuffled deck; reshuffle when exhausted."""
    global _deck
    if not _deck:
        _deck = random.sample(ATTACK_CLASSES, len(ATTACK_CLASSES))
    return _deck.pop(0)


# ── Scheduler state (for /api/demo/status) ────────────────────────────────────
_next_fire_at: Optional[datetime] = None
_last_triggered: Optional[dict] = None


# ── Lazy imports of generators (avoid circular deps at module init) ───────────
def _get_generators():
    from scripts.generate_port_scan_attack import generate_port_scan
    from scripts.generate_ddos_attack import generate_ddos
    from scripts.generate_bruteforce_attack import generate_bruteforce
    from scripts.generate_sql_injection_attack import generate_sql_injection
    from scripts.generate_malware_traffic import generate_malware_traffic
    return {
        "port_scan":     lambda: generate_port_scan(n_ports=40),
        "ddos":          lambda: generate_ddos(n_packets=30),
        "bruteforce":    lambda: generate_bruteforce(n_attempts=25),
        "sql_injection": lambda: generate_sql_injection(n_requests=15),
        "malware":       lambda: generate_malware_traffic(n_packets=20),
    }


# ── Core: fire one attack ─────────────────────────────────────────────────────
def fire_attack(attack_class: Optional[str] = None, *, _from_scheduler: bool = False) -> dict:
    """
    Synchronously fire one attack through the real detection pipeline.

    attack_class — one of ATTACK_CLASSES, or None for a random pick.
                   When called from the scheduler, _from_scheduler=True
                   advances the shuffled rotation; ad-hoc calls use
                   random.choice so the rotation isn't disturbed.
    """
    global _last_triggered

    # Lazy import to avoid circular import at startup
    from backend.app.services.detection_service import DetectionEngine

    if _from_scheduler:
        cls = _next_class()
    else:
        cls = attack_class or random.choice(ATTACK_CLASSES)

    ip = random_public_ip()
    generators = _get_generators()
    rows = generators[cls]()

    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(_DEMO_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_TRAFFIC_HEADER)
        w.writerows(rows)

    try:
        detections = DetectionEngine().run_once()
    finally:
        # Always clean up so the next auto-attack cycle doesn't re-process it
        if _DEMO_FILE.exists():
            _DEMO_FILE.unlink()

    result = {
        "class": cls,
        "ip": ip,
        "at": datetime.now(timezone.utc).isoformat(),
        "detections": len(detections),
    }
    _last_triggered = result
    print(f"[DEMO] {'Scheduled' if _from_scheduler else 'Manual'} trigger: "
          f"{cls} from {ip} → {len(detections)} detection(s)")
    return result


# ── Async scheduler ───────────────────────────────────────────────────────────
async def demo_attack_loop() -> None:
    """
    Runs only when DEMO_MODE=true (started from main.py lifespan).
    Fires one attack per DEMO_INTERVAL_SECONDS in shuffled class rotation.
    """
    global _next_fire_at
    while True:
        _next_fire_at = datetime.now(timezone.utc) + timedelta(seconds=DEMO_INTERVAL_SECONDS)
        await asyncio.sleep(DEMO_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(fire_attack, None, _from_scheduler=True)
        except Exception as exc:
            print(f"[DEMO] Scheduler error: {exc}")


# ── Status snapshot ───────────────────────────────────────────────────────────
def get_status() -> dict:
    remaining: Optional[int] = None
    if _next_fire_at:
        delta = (_next_fire_at - datetime.now(timezone.utc)).total_seconds()
        remaining = max(0, int(delta))
    return {
        "demo_mode": DEMO_MODE,
        "interval_seconds": DEMO_INTERVAL_SECONDS,
        "next_fire_in_seconds": remaining,
        "classes_remaining_in_rotation": list(_deck),
        "last_triggered": _last_triggered,
    }
