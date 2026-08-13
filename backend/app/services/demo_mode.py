"""
Demo / showcase mode — Phase 16.

Runtime toggle — no restart required:
  POST /api/demo/enable  → starts the scheduler immediately
  POST /api/demo/disable → cancels the sleep; in-flight fire still completes
  GET  /api/demo/status  → enabled, next_fire_in_seconds, last_triggered

Env vars set the INITIAL state:
  DEMO_MODE=true           → scheduler starts automatically on boot
  DEMO_INTERVAL_SECONDS=N  → firing cadence (clamped 120–300 s, default 150)

DEMO_MODE=false + no enable call → zero effect on the existing
fast background auto-attack loop (unchanged).

Every attack — scheduled or manual — runs through the exact same
DetectionEngine / MITRE / SHAP / WebSocket pipeline as normal traffic.
"""
import asyncio
import csv
import ipaddress
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.app.core.paths import BASE_DIR

# ── Env vars (read once at import time) ───────────────────────────────────────
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

# ── Private / reserved ranges ─────────────────────────────────────────────────
_RESERVED = [
    ipaddress.IPv4Network("0.0.0.0/8"),
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("100.64.0.0/10"),    # CGNAT
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv4Network("169.254.0.0/16"),   # link-local
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.0.0.0/24"),
    ipaddress.IPv4Network("192.168.0.0/16"),
    ipaddress.IPv4Network("198.18.0.0/15"),    # benchmarking
    ipaddress.IPv4Network("224.0.0.0/4"),      # multicast
    ipaddress.IPv4Network("240.0.0.0/4"),      # reserved
    ipaddress.IPv4Network("255.255.255.255/32"),
]


def random_public_ip() -> str:
    """Return a random globally-routable IPv4, never private/reserved."""
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


# ── Runtime scheduler state ───────────────────────────────────────────────────
# _runtime_enabled: whether the scheduler SHOULD be running
# _scheduler_task:  the live asyncio.Task (None when stopped)
# _next_fire_at:    cleared when scheduler stops, set each sleep cycle

_runtime_enabled: bool = DEMO_MODE   # starts from env var; flipped by enable/disable
_scheduler_task: Optional["asyncio.Task[None]"] = None
_next_fire_at: Optional[datetime] = None
_last_triggered: Optional[dict] = None


# ── Generators (lazy import to avoid circular deps at startup) ─────────────────
def _get_generators() -> dict:
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

    attack_class  — explicit class, or None for a pick.
    _from_scheduler — True advances the shuffled rotation; False uses
                      random.choice so manual triggers don't disturb it.
    """
    global _last_triggered
    from backend.app.services.detection_service import DetectionEngine

    cls = _next_class() if _from_scheduler else (attack_class or random.choice(ATTACK_CLASSES))
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
        if _DEMO_FILE.exists():
            _DEMO_FILE.unlink()

    result = {
        "class": cls,
        "ip": random_public_ip(),
        "at": datetime.now(timezone.utc).isoformat(),
        "detections": len(detections),
    }
    _last_triggered = result
    print(f"[DEMO] {'Scheduled' if _from_scheduler else 'Manual'} → "
          f"{cls} · {len(detections)} detection(s)")
    return result


# ── Internal scheduler loop ───────────────────────────────────────────────────
async def _loop() -> None:
    """
    Sleeps then fires, forever, until cancelled.
    CancelledError is caught so the task exits cleanly without noise.
    The in-flight asyncio.to_thread call completes even after cancel
    (threads aren't interrupted — only the asyncio side is cancelled,
    so the detection run finishes and its results are still WebSocket-pushed).
    """
    global _next_fire_at
    try:
        while True:
            _next_fire_at = datetime.now(timezone.utc) + timedelta(seconds=DEMO_INTERVAL_SECONDS)
            await asyncio.sleep(DEMO_INTERVAL_SECONDS)
            try:
                await asyncio.to_thread(fire_attack, None, _from_scheduler=True)
            except asyncio.CancelledError:
                raise   # propagate — task is being stopped
            except Exception as exc:
                print(f"[DEMO] Scheduler error: {exc}")
    except asyncio.CancelledError:
        pass   # clean exit — not an error
    finally:
        _next_fire_at = None


# ── Public enable / disable ───────────────────────────────────────────────────
async def enable() -> None:
    """
    Start the scheduler immediately (idempotent).
    Safe to call even if already running — does nothing in that case.
    """
    global _scheduler_task, _runtime_enabled
    _runtime_enabled = True
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_loop())
        print(f"[DEMO] Scheduler started (interval={DEMO_INTERVAL_SECONDS}s)")


async def disable() -> None:
    """
    Stop the scheduler immediately (idempotent).
    The current sleep is cancelled at once. Any in-flight fire_attack
    thread runs to completion in the background — its WebSocket push
    still lands, its audit entry is still written.
    """
    global _scheduler_task, _runtime_enabled, _next_fire_at
    _runtime_enabled = False
    _next_fire_at = None
    # Swap the reference out first so enable() can create a new task
    # immediately without racing against the old one's cleanup.
    task, _scheduler_task = _scheduler_task, None
    if task and not task.done():
        task.cancel()
        # Don't await — _loop handles CancelledError internally and exits
        # cleanly; awaiting here would block the HTTP response during the
        # (rare) case where fire_attack is mid-run in a thread.
    if task:
        print("[DEMO] Scheduler stopped")


# ── Status snapshot ───────────────────────────────────────────────────────────
def get_status() -> dict:
    running = _runtime_enabled and _scheduler_task is not None and not _scheduler_task.done()
    remaining: Optional[int] = None
    if running and _next_fire_at:
        delta = (_next_fire_at - datetime.now(timezone.utc)).total_seconds()
        remaining = max(0, int(delta))
    return {
        "enabled": running,
        "interval_seconds": DEMO_INTERVAL_SECONDS,
        "next_fire_in_seconds": remaining,
        "classes_remaining_in_rotation": list(_deck),
        "last_triggered": _last_triggered,
    }
