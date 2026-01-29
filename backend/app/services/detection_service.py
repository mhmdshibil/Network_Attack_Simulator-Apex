# detection_service.py
# This file contains the core logic for the attack detection engine.

import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

from backend.app.ml.model_utils import load_model, predict
from backend.app.ml.feature_engineering import FEATURE_COLUMNS
from backend.app.services.log_service import load_all_logs, aggregate_by_time_window

# Define the base directory and the path to the detections log file.
BASE_DIR = Path(__file__).resolve().parents[3]
DETECTIONS_FILE = BASE_DIR / "data/processed/detections.csv"
# A set to store the IP addresses that have been blocked.
BLOCKED_IPS = set()

class DetectionEngine:
    """
    The main class for the detection engine.
    """
    def __init__(self):
        """
        Initialize the detection engine by loading the machine learning model.
        """
        self.model = load_model()

    def run_once(self):
        """
        Run the detection engine once to process new logs and identify attacks.
        """
        # Load and aggregate the latest logs.
        df = load_all_logs()
        agg = aggregate_by_time_window(df, window_seconds=5)

        # Prepare the features and make predictions.
        X = agg[FEATURE_COLUMNS]
        preds = predict(self.model, X)

        # Add the predictions to the aggregated DataFrame.
        agg["predicted_label"] = preds

        detections = []

        # Filter for attacks (i.e., predictions that are not "normal").
        attacks = agg[agg["predicted_label"] != "normal"]

        # Process each detected attack.
        for _, row in attacks.iterrows():
            ip = row["source_ip"]
            timestamp = datetime.now(timezone.utc).isoformat()

            # Add the IP address to the set of blocked IPs.
            BLOCKED_IPS.add(ip)

            # Create a dictionary to represent the detection event.
            detection = {
                "ip": ip,
                "timestamp": timestamp,
                "label": row["predicted_label"],
                "action": "blocked"
            }

            detections.append(detection)
            # Log the detection to a file.
            self._log_detection(detection)

            # Print an alert and a simulated firewall rule.
            print(f"[ALERT] Attack detected from {ip}")
            print(f"[SIMULATED FIREWALL] iptables -A INPUT -s {ip} -j DROP")

        # Return the list of detections.
        return detections

    def _log_detection(self, detection):
        """
        Log a detection event to the detections CSV file.
        """
        # Create a DataFrame from the detection dictionary.
        df = pd.DataFrame([detection])

        # Append the detection to the CSV file.
        if DETECTIONS_FILE.exists():
            df.to_csv(DETECTIONS_FILE, mode="a", header=False, index=False)
        else:
            df.to_csv(DETECTIONS_FILE, index=False)
