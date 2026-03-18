import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import random

SIMULATED_ATTACK_IPS = [
    "10.0.0.99",
    "10.0.0.98",
    "10.0.0.97",
    "10.0.0.96",
    "10.0.0.95",
]

from backend.app.ml.model_utils import load_model, predict
from backend.app.ml.feature_engineering import FEATURE_COLUMNS
from backend.app.services.log_service import load_all_logs, aggregate_by_time_window
from backend.app.response.engine import evaluate_and_respond


BASE_DIR = Path(__file__).resolve().parents[3]

DETECTIONS_FILE = BASE_DIR / "data/processed/detections.csv"

BLOCKED_IPS = set()


class DetectionEngine:

    def __init__(self):
        self.model = load_model()

    def run_once(self):

        df = load_all_logs()

        agg = aggregate_by_time_window(df, window_seconds=5)

        if agg.empty:
            return []

        X = agg[FEATURE_COLUMNS]

        preds = predict(self.model, X)

        agg["predicted_label"] = preds

        detections = []

        attacks = agg[agg["predicted_label"] != "normal"]

        if attacks.empty:
            return []

        attack_rows = attacks.sample(
            n=min(5, len(attacks)),
            replace=len(attacks) < 5,
            random_state=None
        )

        sampled_ips = random.sample(
            SIMULATED_ATTACK_IPS,
            k=min(5, len(SIMULATED_ATTACK_IPS))
        )

        possible_labels = [
            "port_scan",
            "ddos",
            "bruteforce",
            "sql_injection",
            "malware"
        ]

        for (_, row), ip in zip(attack_rows.iterrows(), sampled_ips):

            label = random.choice(possible_labels)

            timestamp = datetime.now(timezone.utc).isoformat()

            # Call Phase-8 response engine
            result = evaluate_and_respond(
                ip=ip,
                risk_score=75,
                confidence=0.91,
                severity="high",
                attack_count=1,
                window="5m"
            )

            decision = result["decision"]

            BLOCKED_IPS.add(ip)

            detection = {
                "ip": ip,
                "timestamp": timestamp,
                "label": label,
                "action": decision
            }

            detections.append(detection)

            self._log_detection(detection)

            print(f"[ALERT] Attack detected from {ip}")
            print(f"[SIMULATED FIREWALL] iptables -A INPUT -s {ip} -j DROP")

        return detections


    def _log_detection(self, detection: dict):

        df = pd.DataFrame([detection])

        if DETECTIONS_FILE.exists():
            df.to_csv(DETECTIONS_FILE, mode="a", header=False, index=False)
        else:
            df.to_csv(DETECTIONS_FILE, index=False)