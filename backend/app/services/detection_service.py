# backend/app/services/detection_service.py
# This module contains the core logic for the attack detection engine. The `DetectionEngine` class
# is responsible for orchestrating the entire detection process, from loading raw log data to
# making predictions with a trained machine learning model. It identifies potential attacks by
# analyzing aggregated network traffic data and, upon detection, logs the event and simulates a
# response action, such as blocking an IP address.

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

# The base directory of the project, used to construct absolute paths.
BASE_DIR = Path(__file__).resolve().parents[3]
# The path to the CSV file where all detected attack events are logged.
DETECTIONS_FILE = BASE_DIR / "data/processed/detections.csv"
# A set to maintain an in-memory record of all IP addresses that have been blocked.
BLOCKED_IPS = set()

class DetectionEngine:
    """
    The main class for the detection engine, responsible for identifying attacks.
    """
    def __init__(self):
        """
        Initializes the DetectionEngine by loading the pre-trained machine learning model.
        The model is loaded once upon instantiation to ensure efficient and repeated use.
        """
        self.model = load_model()

    def run_once(self):
        """
        Executes a single run of the detection pipeline.

        This method performs the following steps:
        1. Loads all available log data.
        2. Aggregates the logs into time-based windows to create features.
        3. Uses the loaded machine learning model to make predictions on the aggregated data.
        4. Filters for predictions that are classified as attacks (i.e., not 'normal').
        5. For each detected attack, it logs the event, adds the IP to the `BLOCKED_IPS` set,
           and simulates a response by printing an alert and a firewall rule.

        Returns:
            list: A list of dictionaries, where each dictionary represents a new detection event.
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

        # Simulate up to 5 attack events per run.
        attack_rows = attacks.sample(
            n=5,
            replace=len(attacks) < 5,
            random_state=None
        )
        
        sampled_ips = random.sample(
            SIMULATED_ATTACK_IPS,
            k=min(5, len(SIMULATED_ATTACK_IPS))
        )
        
        possible_labels = ["port_scan", "ddos", "bruteforce", "sql_injection", "malware"]
        
        for ( _, row), ip in zip(attack_rows.iterrows(), sampled_ips):
            label = random.choice(possible_labels)
            timestamp = datetime.now(timezone.utc).isoformat()

            # Add the IP address to the set of blocked IPs.
            BLOCKED_IPS.add(ip)

            # Create a dictionary to represent the detection event.
            detection = {
                "ip": ip,
                "timestamp": timestamp,
                "label": label,
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

    def _log_detection(self, detection: dict):
        """
        Logs a single detection event to the `detections.csv` file.

        This method takes a detection dictionary, converts it into a pandas DataFrame, and appends
        it to the CSV file. If the file does not exist, it will be created with a header.

        Args:
            detection (dict): A dictionary representing the detection event.
        """
        # Create a DataFrame from the detection dictionary.
        df = pd.DataFrame([detection])

        # Append the detection to the CSV file.
        if DETECTIONS_FILE.exists():
            df.to_csv(DETECTIONS_FILE, mode="a", header=False, index=False)
        else:
            df.to_csv(DETECTIONS_FILE, index=False)
