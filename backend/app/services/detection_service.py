import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

from backend.app.ml.model_utils import load_model, predict
from backend.app.ml.feature_engineering import FEATURE_COLUMNS
from backend.app.services.log_service import load_all_logs, aggregate_by_time_window

BASE_DIR = Path(__file__).resolve().parents[3]
DETECTIONS_FILE = BASE_DIR / "data/processed/detections.csv"
BLOCKED_IPS = set()

class DetectionEngine:
    def __init__(self):
        self.model = load_model()

    def run_once(self):
        df = load_all_logs()
        agg = aggregate_by_time_window(df, window_seconds=5)

        X = agg[FEATURE_COLUMNS]
        preds = predict(self.model, X)

        agg["predicted_label"] = preds

        detections = []

        attacks = agg[agg["predicted_label"] != "normal"]

        for _, row in attacks.iterrows():
            ip = row["source_ip"]
            timestamp = datetime.now(timezone.utc).isoformat()

            BLOCKED_IPS.add(ip)

            detection = {
                "ip": ip,
                "timestamp": timestamp,
                "label": row["predicted_label"],
                "action": "blocked"
            }

            detections.append(detection)
            self._log_detection(detection)

            print(f"[ALERT] Attack detected from {ip}")
            print(f"[SIMULATED FIREWALL] iptables -A INPUT -s {ip} -j DROP")

        return detections

    def _log_detection(self, detection):
        df = pd.DataFrame([detection])

        if DETECTIONS_FILE.exists():
            df.to_csv(DETECTIONS_FILE, mode="a", header=False, index=False)
        else:
            df.to_csv(DETECTIONS_FILE, index=False)
