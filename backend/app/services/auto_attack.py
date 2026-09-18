"""
Background loop: generate synthetic traffic for all attack classes every 8-12 s.

Relative frequencies (attacks are rarer than normal traffic):
  normal         60 rows  (always included)
  port_scan      40 rows  — weight 4
  ddos           30 rows  — weight 3
  bruteforce     25 rows  — weight 2
  malware        20 rows  — weight 2
  sql_injection  15 rows  — weight 1
"""
import asyncio
import csv
import os
import random

from backend.app.core.paths import BASE_DIR

from scripts.generate_normal_traffic import generate_normal_traffic
from scripts.generate_port_scan_attack import generate_port_scan
from scripts.generate_ddos_attack import generate_ddos
from scripts.generate_bruteforce_attack import generate_bruteforce
from scripts.generate_sql_injection_attack import generate_sql_injection
from scripts.generate_malware_traffic import generate_malware_traffic

_enabled: bool = True

# Traffic profile selector (additive — "default" preserves original behavior).
TRAFFIC_PROFILE = os.getenv("TRAFFIC_PROFILE", "default").lower()

_RAW_DIR = BASE_DIR / "data" / "raw"

_TRAFFIC_HEADER = [
    "timestamp", "source_ip", "destination_ip", "destination_port",
    "protocol", "packet_count", "request_rate", "success_flag", "label",
]

# (generator_fn, kwargs, output_filename, weight)
_ATTACK_GENERATORS = [
    (generate_port_scan,       {"n_ports": 40},       "port_scan.csv",    4),
    (generate_ddos,            {"n_packets": 30},     "ddos.csv",         3),
    (generate_bruteforce,      {"n_attempts": 25},    "bruteforce.csv",   2),
    (generate_malware_traffic, {"n_packets": 20},     "malware.csv",      2),
    (generate_sql_injection,   {"n_requests": 15},    "sql_injection.csv",1),
]


def _write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_TRAFFIC_HEADER)
        w.writerows(rows)


def _clear_raw_dir() -> None:
    """Remove all generated attack/normal CSVs so no stale schema lingers."""
    for p in _RAW_DIR.glob("*.csv"):
        p.unlink()


def _run_college_cycle() -> None:
    """Write a single college-profile window (10-column schema incl. target_zone)."""
    from scripts.college_profile import CollegeNetworkProfile

    profile = CollegeNetworkProfile()
    rows = profile.generate_window()
    path = _RAW_DIR / "college_traffic.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CollegeNetworkProfile.TRAFFIC_HEADER)
        w.writerows(rows)


def _run_cycle() -> int:
    from backend.app.services.detection_service import DetectionEngine

    _RAW_DIR.mkdir(parents=True, exist_ok=True)

    if TRAFFIC_PROFILE == "college":
        # College profile owns the whole window; clear stale files first so the
        # raw dir holds only the 10-column college schema.
        _clear_raw_dir()
        _run_college_cycle()
    else:
        # Default behavior (unchanged).
        # Always write normal traffic
        _write_csv(_RAW_DIR / "normal_traffic.csv", generate_normal_traffic(n=60))

        # Pick one attack type per cycle (weighted random)
        population = [g for g in _ATTACK_GENERATORS]
        weights = [g[3] for g in population]
        fn, kwargs, filename, _ = random.choices(population, weights=weights, k=1)[0]
        _write_csv(_RAW_DIR / filename, fn(**kwargs))

        # Remove stale files from other attack types so they don't persist
        for _, _, fname, _ in _ATTACK_GENERATORS:
            if fname != filename:
                p = _RAW_DIR / fname
                if p.exists():
                    p.unlink()

    detections = DetectionEngine().run_once()
    return len(detections)


async def auto_attack_loop() -> None:
    print(f"[AUTO] Traffic profile: {TRAFFIC_PROFILE}")
    while True:
        if _enabled:
            try:
                n = await asyncio.to_thread(_run_cycle)
                print(f"[AUTO] Attack cycle complete — {n} new detection(s)")
            except Exception as exc:
                print(f"[AUTO] Cycle error: {exc}")
        await asyncio.sleep(random.uniform(8, 12))


def set_enabled(value: bool) -> None:
    global _enabled
    _enabled = value


def is_enabled() -> bool:
    return _enabled
