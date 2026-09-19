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

# Optional PostgreSQL/SQLite sink (Phase 2). Guarded so the app still runs and
# detects when the DB deps are not installed — CSV/JSONL remain the fallback.
try:
    from backend.app.core import database as _db
except Exception as _db_exc:  # pragma: no cover
    _db = None
    print(f"[DB] database layer unavailable ({_db_exc}); using CSV/JSONL only")

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

            # Passthrough: carry target_zone (mode of the group) if present so it
            # survives to the WebSocket broadcast for NetworkMap.jsx.
            if "target_zone" in ip_group.columns:
                tz_vals = ip_group["target_zone"].dropna()
                target_zone = tz_vals.mode().iloc[0] if not tz_vals.empty else None
            else:
                target_zone = None

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
                "target_zone": target_zone,
                "shap_top3": shap_top3,
                "mitre": mitre,
            }

            # Threat-intel enrichment (threat_score + possible BLOCK escalation)
            self._enrich_threat_intel(detection)
            action = detection["action"]

            detections.append(detection)
            self._log_detection(detection)          # CSV (primary/fallback)

            # Dual-write to DB (non-blocking, guarded — CSV is the fallback)
            if _db is not None:
                _db.save_detection_safe(
                    ip=alert_ip, timestamp=timestamp, label=label, action=detection["action"],
                    risk_score=detection["risk_score"], confidence=confidence,
                    target_zone=target_zone,
                    packets_per_second=float(representative_row.get("packets_per_second", 0) or 0),
                    avg_request_rate=float(representative_row.get("avg_request_rate", 0) or 0),
                    failed_connections=representative_row.get("failed_connections"),
                    unique_ports=representative_row.get("unique_ports"),
                    mitre_tactic=(mitre or {}).get("tactic"),
                    mitre_technique=(mitre or {}).get("technique_id"),
                    sensor_mode="auto",
                )

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

    def process_features(
        self,
        *,
        source_ip: str,
        packets_per_second: float,
        avg_request_rate: float,
        failed_connections: float,
        unique_ports: float,
        bytes_per_packet: float = 300.0,
        connection_duration: float = 2.0,
        payload_entropy: float = 4.0,
        target_zone: str | None = None,
        timestamp: str | None = None,
        sensor_mode: str = "demo",
    ) -> dict:
        """
        Run the detection pipeline on a single externally-supplied feature window
        (e.g. from sensor_agent.py via POST /api/detections).

        Reuses the same model, response engine, SHAP, MITRE, logging and
        WebSocket broadcast as run_once — only the feature source differs, and
        the caller's real source_ip is preserved (not randomised). Attacks are
        logged + broadcast (with target_zone); normal traffic is returned only.
        """
        ts = timestamp or datetime.now(timezone.utc).isoformat()

        X = pd.DataFrame(
            [[packets_per_second, avg_request_rate, failed_connections, unique_ports,
              bytes_per_packet, connection_duration, payload_entropy]],
            columns=FEATURE_COLUMNS,
        )

        # ── Random Forest + Isolation Forest (same as run_once) ─────────────
        rf_label = predict(self.model, X)[0]
        probas = predict_proba(self.model, X)
        rf_conf = float(probas.max(axis=1)[0]) if probas is not None else 0.6
        anomalous = bool(is_anomalous(self.anomaly_model, X)[0])
        score = float(anomaly_score(self.anomaly_model, X)[0])

        # ── Resolve final label (identical rule to run_once._resolve) ───────
        if rf_label != "normal":
            label, confidence = rf_label, rf_conf
        elif anomalous:
            label, confidence = "unknown_anomaly", min(score * 1.5, 0.75)
        else:
            label, confidence = "normal", 0.0

        risk_score = round(min(confidence * 100, 99.0), 1)
        severity = _confidence_to_severity(confidence)

        result = evaluate_and_respond(
            ip=source_ip,
            risk_score=risk_score,
            confidence=confidence,
            severity=severity,
            attack_count=1,
            window="5s",
        )
        decision = result["decision"]
        action = _DECISION_TO_ACTION.get(decision, decision.lower())

        # ── SHAP — only for real detections ─────────────────────────────────
        shap_top3 = []
        if label != "normal":
            shap_label = label if label in self.classes_ else rf_label
            try:
                shap_top3 = explain_row(self.model, X.iloc[0], shap_label)
                store_explanation(source_ip, ts, label, shap_top3)
            except Exception as shap_err:
                print(f"[SHAP] Error: {shap_err}")

        detection = {
            "ip": source_ip,
            "timestamp": ts,
            "label": label,
            "action": action,
            "risk_score": result.get("risk_score", risk_score),
            "confidence": round(confidence, 3),
            "rf_label": rf_label,
            "if_anomalous": anomalous,
            "target_zone": target_zone,
            "shap_top3": shap_top3,
            "mitre": get_mitre(label),
        }

        # Persist + broadcast only actual detections (attacks), like run_once.
        if label != "normal":
            # Threat-intel enrichment (threat_score + possible BLOCK escalation)
            self._enrich_threat_intel(detection)
            action = detection["action"]

            self._log_detection(detection)          # CSV (primary/fallback)

            # Dual-write to DB (non-blocking, guarded — CSV is the fallback)
            if _db is not None:
                _db.save_detection_safe(
                    ip=source_ip, timestamp=ts, label=label, action=detection["action"],
                    risk_score=detection["risk_score"], confidence=confidence,
                    target_zone=target_zone,
                    packets_per_second=packets_per_second,
                    avg_request_rate=avg_request_rate,
                    failed_connections=failed_connections,
                    unique_ports=unique_ports,
                    mitre_tactic=(detection["mitre"] or {}).get("tactic"),
                    mitre_technique=(detection["mitre"] or {}).get("technique_id"),
                    sensor_mode=sensor_mode,
                )

            ws_manager.broadcast_sync({
                "type": "detection",
                **{k: v for k, v in detection.items() if k != "shap_top3"},
            })
            print(
                f"[INGEST] {action.upper()} — {label} from {source_ip} "
                f"(risk={risk_score:.0f}, conf={confidence:.2f}, zone={target_zone})"
            )

        return detection

    def _enrich_threat_intel(self, detection: dict) -> None:
        """
        Attach threat_score to a detection and escalate to BLOCK when > 80.

        Reads the TI cache synchronously (DB only, no network) so the score can
        ride along in the same WebSocket broadcast, then fires a non-blocking
        live refresh so the next detection for this IP is enriched. Fully
        guarded — TI/DB failures never break a detection.
        """
        detection.setdefault("threat_score", None)
        if _db is None:
            return
        ip = detection.get("ip")
        try:
            from backend.app.services.threat_intel_service import service as ti
        except Exception:
            return
        try:
            cached = _db.run_async(_db.get_ip_reputation(ip), timeout=3)
        except Exception:
            cached = None
        if cached:
            score = ti.compute_threat_score(
                cached.get("abuse_score"), cached.get("vt_malicious"), cached.get("is_known_bad"))
            detection["threat_score"] = score
            if score is not None and score > 80:
                detection["action"] = "blocked"   # override decide_action regardless of attack_count
        # Fire-and-forget live refresh (updates the cache for next time).
        try:
            _db.run_async_bg(ti.check_ip(ip))
        except Exception:
            pass

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

        # Auto-create triage case for every attack detection (non-blocking)
        if _db is not None:
            try:
                _db.create_triage_case_safe(
                    detection_id=f"{detection['ip']}:{detection['timestamp']}",
                    ip=detection["ip"],
                    label=detection["label"],
                    risk_score=detection.get("risk_score", 0),
                )
            except Exception:
                pass

        # Notification triggers (Phase 3 / Task 3)
        try:
            from backend.app.services.notification_service import service as _notify
            _notify.maybe_notify(detection)
        except Exception:
            pass
