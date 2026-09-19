"""
seed_detections.py
Run this from your project root to inject fresh detection data:
    python seed_detections.py

This adds realistic detections for the past 2 hours so that
the 5m, 1h, and 24h timeline views all show data.
"""

import csv
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── adjust this path if your detections.csv lives elsewhere ──
DETECTIONS_FILE = Path("data/processed/detections.csv")

LABELS = ["ddos", "port_scan", "sql_injection", "bruteforce", "malware"]
ACTIONS = ["blocked", "monitored", "rate_limited"]

SAMPLE_IPS = [
    "192.168.1.11", "10.0.0.52", "172.14.0.23",
    "203.0.123.42", "198.11.100.7", "192.0.2.87","171.0.0"
]

def generate_rows(hours_back: int = 2, rows_per_minute: int = 3) -> list[dict]:
    rows = []
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours_back)
    current = start

    while current <= now:
        # Randomly skip some minutes to make it look realistic
        if random.random() > 0.3:
            for _ in range(random.randint(1, rows_per_minute)):
                rows.append({
                    "ip": random.choice(SAMPLE_IPS),
                    "timestamp": current.isoformat(),
                    "label": random.choice(LABELS),
                    "action": random.choices(
                        ACTIONS, weights=[0.5, 0.3, 0.2]
                    )[0]
                })
        current += timedelta(minutes=1)

    return rows

def seed():
    DETECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing_rows = []

    # Preserve existing data
    if DETECTIONS_FILE.exists():
        with open(DETECTIONS_FILE, newline="") as f:
            reader = csv.DictReader(f, fieldnames=["ip", "timestamp", "label", "action"])
            existing_rows = list(reader)
        print(f"Found {len(existing_rows)} existing rows — preserving them.")

    new_rows = generate_rows(hours_back=2, rows_per_minute=3)
    print(f"Generating {len(new_rows)} new rows...")

    all_rows = existing_rows + new_rows

    with open(DETECTIONS_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ip", "timestamp", "label", "action"])
        writer.writerows(all_rows)

    print(f"Done! Total rows in detections.csv: {len(all_rows)}")
    print(f"Date range: last 2 hours up to now ({datetime.now(timezone.utc).isoformat()})")
    print("\nNow restart your FastAPI server and refresh the dashboard.")

if __name__ == "__main__":
    seed()
