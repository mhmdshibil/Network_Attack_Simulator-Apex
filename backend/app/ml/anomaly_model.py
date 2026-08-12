"""
Isolation Forest anomaly detector — Phase 3.

Trained only on normal traffic. Runs alongside the Random Forest classifier:
  - RF says "attack" + IF says anomalous  → high-confidence known attack
  - RF says "normal" + IF says anomalous  → label = "unknown_anomaly" (zero-day path)
  - RF says "attack" + IF says normal     → possible FP, lower confidence
  - RF says "normal" + IF says normal     → benign
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.app.ml.feature_engineering import FEATURE_COLUMNS
from backend.app.ml.attack_taxonomy import ATTACK_CLASSES
from backend.app.core.paths import ANOMALY_MODEL_PATH


def train_isolation_forest(contamination: float = 0.02) -> IsolationForest:
    """
    Train on a mix of:
      - Synthetic normal samples (full taxonomy range)
      - Actual aggregated windows from the live normal traffic generator
        so the IF sees the real sparse-window distribution.
    """
    from backend.app.ml.dataset_generator import generate_samples
    from scripts.generate_normal_traffic import generate_normal_traffic
    from backend.app.services.log_service import aggregate_by_time_window

    # Synthetic taxonomy-based normal samples
    synthetic_rows = generate_samples("normal", n=3000)
    X_synth = pd.DataFrame(synthetic_rows)[FEATURE_COLUMNS]

    # Real aggregated windows (run generator 20 times to get diverse samples)
    agg_frames = []
    for _ in range(20):
        raw_rows = generate_normal_traffic(n=200)
        raw_df = pd.DataFrame(raw_rows, columns=[
            "timestamp", "source_ip", "destination_ip", "destination_port",
            "protocol", "packet_count", "request_rate", "success_flag", "label",
        ])
        agg = aggregate_by_time_window(raw_df, window_seconds=5)
        if not agg.empty:
            agg_frames.append(agg[FEATURE_COLUMNS])

    X_parts = [X_synth]
    if agg_frames:
        X_parts.append(pd.concat(agg_frames, ignore_index=True))

    X = pd.concat(X_parts, ignore_index=True).dropna()
    print(f"[IF] Training on {len(X)} normal samples ({len(agg_frames)*200} real-traffic rows included)")

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X)

    ANOMALY_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ANOMALY_MODEL_PATH)
    print(f"[OK] Isolation Forest saved: {ANOMALY_MODEL_PATH}")
    return model


def load_anomaly_model() -> IsolationForest | None:
    if not ANOMALY_MODEL_PATH.exists():
        return None
    return joblib.load(ANOMALY_MODEL_PATH)


def is_anomalous(model: IsolationForest, X: pd.DataFrame) -> np.ndarray:
    """Return boolean array: True = anomalous (outlier)."""
    if model is None:
        return np.zeros(len(X), dtype=bool)
    preds = model.predict(X)   # sklearn: -1 = outlier, 1 = inlier
    return preds == -1


def anomaly_score(model: IsolationForest, X: pd.DataFrame) -> np.ndarray:
    """Return raw anomaly scores (higher = more anomalous, range ~ [-0.5, 0.5])."""
    if model is None:
        return np.zeros(len(X))
    return -model.score_samples(X)   # negate so higher = more anomalous


if __name__ == "__main__":
    train_isolation_forest()
