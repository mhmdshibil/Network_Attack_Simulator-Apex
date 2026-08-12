"""
DetectionEngine — Phase 1 + Phase 3 combined.

Data flow:
  raw CSV logs
    → aggregate_by_time_window (5 s windows, 4 features)
    → Random Forest predict + predict_proba
    → Isolation Forest anomaly score
    → label / confidence / risk derived from model output (no random overrides)
    → evaluate_and_respond (policy decision)
    → append to detections.csv + audit log
"""
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from backend.app.ml.model_utils import load_model, predict, predict_proba
from backend.app.ml.anomaly_model import load_anomaly_model, is_anomalous, anomaly_score
from backend.app.ml.feature_engineering import FEATURE_COLUMNS
from backend.app.ml.shap_explainer import explain_row, store_explanation
from backend.app.ml.mitre_mapping import get_mitre
from backend.app.services.log_service import load_all_logs, aggregate_by_time_window
from backend.app.services.ws_manager import manager as ws_manager
from backend.app.response.engine import evaluate_and_respond
from backend.app.core.paths import DETECTIONS_FILE

import random

_EXTERNAL_FIRST_OCTETS = [45, 80, 89, 91, 103, 146, 185, 194, 198, 222]


def _random_external_ip() -> str:
    first = random.choice(_EXTERNAL_FIRST_OCTETS)
    return f"{first}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"


def _confidence_to_severity(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.65:
        return "medium"
    return "low"


_DECISION_TO_ACTION = {
    "BLOCK": "blocked",
    "RATE_LIMIT": "rate_limited",
    "MONITOR": "monitored",
    "ALLOW": "allowed",
}


class DetectionEngine:

    def __init__(self):
        self.model = load_model()
        self.anomaly_model = load_anomaly_model()
        # Cache class order for predict_proba column mapping
        self.classes_ = list(self.model.classes_)

    def run_once(self) -> list[dict]:
        df = load_all_logs()
        agg = aggregate_by_time_window(df, window_seconds=5)

        if agg.empty:
            return []

        X = agg[FEATURE_COLUMNS]

        # ── Random Forest ──────────────────────────────────────────────────
        rf_labels = predict(self.model, X)
        probas = predict_proba(self.model, X)  # shape (n_rows, n_classes)

        agg = agg.copy()
        agg["rf_label"] = rf_labels
        if probas is not None:
            agg["rf_confidence"] = probas.max(axis=1)
        else:
            agg["rf_confidence"] = 0.6

        # ── Isolation Forest ───────────────────────────────────────────────
        anomalous = is_anomalous(self.anomaly_model, X)
        scores = anomaly_score(self.anomaly_model, X)
        agg["if_anomalous"] = anomalous
        agg["if_score"] = scores

        # ── Resolve final label ────────────────────────────────────────────
        # RF says attack → use its label
        # RF says normal + IF says anomalous → "unknown_anomaly" (zero-day path)
        # Both say normal → skip

        def _resolve(row):
            if row["rf_label"] != "normal":
                return row["rf_label"], float(row["rf_confidence"])
            if row["if_anomalous"]:
                # Confidence proportional to anomaly score (capped at 0.75)
                conf = min(float(row["if_score"]) * 1.5, 0.75)
                return "unknown_anomaly", conf
            return "normal", 0.0

        labels_confs = agg.apply(lambda r: _resolve(r), axis=1)
        agg["final_label"] = [lc[0] for lc in labels_confs]
        agg["final_conf"] = [lc[1] for lc in labels_confs]

        # Keep attack rows only
        attacks = agg[agg["final_label"] != "normal"]
        if attacks.empty:
            return []

        detections = []

        # Group by source IP so attack_count reflects events per IP
        for source_ip, ip_group in attacks.groupby("source_ip"):
            label = ip_group["final_label"].value_counts().index[0]
            confidence = float(ip_group["final_conf"].mean())
            risk_score = round(min(confidence * 100, 99.0), 1)
            severity = _confidence_to_severity(confidence)
            attack_count = len(ip_group)

            # Replace internal sim IP with a plausible external address
            alert_ip = _random_external_ip()
            timestamp = datetime.now(timezone.utc).isoformat()

            result = evaluate_and_respond(
                ip=alert_ip,
                risk_score=risk_score,
                confidence=confidence,
                severity=severity,
                attack_count=attack_count,
                window="5m",
            )

            decision = result["decision"]
            action = _DECISION_TO_ACTION.get(decision, decision.lower())

            # SHAP — for unknown_anomaly, explain via the RF's actual label
            rf_label_for_shap = ip_group["rf_label"].value_counts().index[0]
            shap_label = label if label in self.classes_ else rf_label_for_shap
            representative_row = ip_group.iloc[0]
            try:
                shap_top3 = explain_row(self.model, representative_row, shap_label)
                store_explanation(alert_ip, timestamp, label, shap_top3)
            except Exception as shap_err:
                shap_top3 = []
                print(f"[SHAP] Error: {shap_err}")

            mitre = get_mitre(label)
            detection = {
                "ip": alert_ip,
                "timestamp": timestamp,
                "label": label,
                "action": action,
                "risk_score": result.get("risk_score", risk_score),
                "confidence": round(confidence, 3),
                "rf_label": ip_group["rf_label"].value_counts().index[0],
                "if_anomalous": bool(ip_group["if_anomalous"].any()),
                "shap_top3": shap_top3,
                "mitre": mitre,
            }

            detections.append(detection)
            self._log_detection(detection)

            # Broadcast to WebSocket clients
            ws_manager.broadcast_sync({
                "type": "detection",
                **{k: v for k, v in detection.items() if k != "shap_top3"},
            })

            print(
                f"[ALERT] {action.upper()} — {label} from {alert_ip} "
                f"(risk={risk_score:.0f}, conf={confidence:.2f}, "
                f"rf={detection['rf_label']}, if_anom={detection['if_anomalous']})"
            )

        return detections

    def _log_detection(self, detection: dict):
        # Write the 5 core columns that all analytics routes expect
        row = pd.DataFrame([{
            "ip": detection["ip"],
            "timestamp": detection["timestamp"],
            "label": detection["label"],
            "action": detection["action"],
            "risk_score": detection["risk_score"],
        }])

        if DETECTIONS_FILE.exists():
            row.to_csv(DETECTIONS_FILE, mode="a", header=False, index=False)
        else:
            DETECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            row.to_csv(DETECTIONS_FILE, index=False)
