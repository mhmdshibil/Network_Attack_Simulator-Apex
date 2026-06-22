import asyncio
import csv
import random

from backend.app.core.paths import BASE_DIR
from scripts.generate_port_scan_attack import generate_port_scan
from scripts.generate_normal_traffic import generate_normal_traffic

_enabled: bool = True

_RAW_DIR = BASE_DIR / "data" / "raw"
_PORT_SCAN_FILE = _RAW_DIR / "port_scan.csv"
_NORMAL_FILE = _RAW_DIR / "normal_traffic.csv"

_TRAFFIC_HEADER = [
    "timestamp", "source_ip", "destination_ip", "destination_port",
    "protocol", "packet_count", "request_rate", "success_flag", "label",
]


def _run_cycle() -> int:
    """Generate synthetic traffic, overwrite raw files, run detection. Returns new detection count."""
    # Lazy import avoids triggering model load at module import time.
    from backend.app.services.detection_service import DetectionEngine

    _RAW_DIR.mkdir(parents=True, exist_ok=True)

    attack_rows = generate_port_scan(n_ports=40)
    normal_rows = generate_normal_traffic(n=60)

    with open(_PORT_SCAN_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_TRAFFIC_HEADER)
        w.writerows(attack_rows)

    with open(_NORMAL_FILE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_TRAFFIC_HEADER)
        w.writerows(normal_rows)

    detections = DetectionEngine().run_once()
    return len(detections)


async def auto_attack_loop() -> None:
    """Background async loop: generate traffic + run detection every 8-12 s."""
    while True:
        if _enabled:
            try:
                n = await asyncio.to_thread(_run_cycle)
                print(f"[AUTO] Generated attack batch, {n} new detections")
            except Exception as exc:
                print(f"[AUTO] Cycle error: {exc}")
        await asyncio.sleep(random.uniform(8, 12))


def set_enabled(value: bool) -> None:
    global _enabled
    _enabled = value


def is_enabled() -> bool:
    return _enabled
