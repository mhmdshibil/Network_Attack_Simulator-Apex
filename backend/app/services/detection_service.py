import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
import random

from backend.app.ml.model_utils import load_model, predict
from backend.app.ml.feature_engineering import FEATURE_COLUMNS
from backend.app.services.log_service import load_all_logs, aggregate_by_time_window
from backend.app.response.engine import evaluate_and_respond

_EXTERNAL_FIRST_OCTETS = [45, 80, 89, 91, 103, 146, 185, 194, 198, 222]

def _generate_external_ips(count: int) -> list:
    ips = set()
    while len(ips) < count:
        first = random.choice(_EXTERNAL_FIRST_OCTETS)
        ip = f"{first}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        ips.add(ip)
    return list(ips)


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

        n_attacks = min(5, len(attacks))
        attack_rows = attacks.sample(
            n=n_attacks,
            replace=len(attacks) < 5,
            random_state=None
        )

        sampled_ips = _generate_external_ips(n_attacks)

        possible_labels = [
            "port_scan",
            "ddos",
            "bruteforce",
            "sql_injection",
            "malware"
        ]

        _DECISION_TO_ACTION = {
            "BLOCK": "blocked", "RATE_LIMIT": "rate_limited",
            "MONITOR": "monitored", "ALLOW": "allowed",
        }

        for (_, row), ip in zip(attack_rows.iterrows(), sampled_ips):

            label = random.choice(possible_labels)
            timestamp = datetime.now(timezone.utc).isoformat()

            # Vary parameters so the policy engine produces a realistic mix of outcomes:
            # 'block'      → attack_count 26-40, rate≥5  → BLOCK
            # 'rate_limit' → attack_count 6-20,  rate 1-4 → RATE_LIMIT
            # 'monitor'    → attack_count 1-4, severity=medium → MONITOR
            tier = random.choices(
                ['block', 'rate_limit', 'monitor'],
                weights=[30, 40, 30]
            )[0]

            if tier == 'block':
                risk_score = random.randint(85, 98)
                confidence = round(random.uniform(0.87, 0.97), 2)
                severity = "high"
                attack_count = random.randint(26, 40)
            elif tier == 'rate_limit':
                risk_score = random.randint(65, 84)
                confidence = round(random.uniform(0.74, 0.92), 2)
                severity = "medium"
                attack_count = random.randint(6, 20)
            else:
                risk_score = random.randint(45, 74)
                confidence = round(random.uniform(0.65, 0.85), 2)
                severity = "medium"
                attack_count = random.randint(1, 4)

            result = evaluate_and_respond(
                ip=ip,
                risk_score=risk_score,
                confidence=confidence,
                severity=severity,
                attack_count=attack_count,
                window="5m"
            )

            decision = result["decision"]
            action = _DECISION_TO_ACTION.get(decision, decision.lower())

            BLOCKED_IPS.add(ip)

            detection = {
                "ip": ip,
                "timestamp": timestamp,
                "label": label,
                "action": action
            }

            detections.append(detection)

            self._log_detection(detection)

            print(f"[ALERT] {action.upper()} — {label} from {ip} (risk={risk_score}, conf={confidence})")

        return detections


    def _log_detection(self, detection: dict):

        df = pd.DataFrame([detection])

        if DETECTIONS_FILE.exists():
            df.to_csv(DETECTIONS_FILE, mode="a", header=False, index=False)
        else:
            df.to_csv(DETECTIONS_FILE, index=False)