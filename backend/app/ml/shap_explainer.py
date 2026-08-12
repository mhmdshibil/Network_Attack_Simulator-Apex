"""
SHAP explainability — Phase 5.

Computes top-3 feature contributions for each Random Forest detection.
Uses TreeExplainer (fast, exact for tree ensembles).
"""
import json
import numpy as np
import pandas as pd
import shap

from backend.app.ml.feature_engineering import FEATURE_COLUMNS
from backend.app.core.paths import PROCESSED_DIR

_SHAP_FILE = PROCESSED_DIR / "shap_explanations.jsonl"

_explainer_cache: shap.TreeExplainer | None = None


def get_explainer(model) -> shap.TreeExplainer:
    global _explainer_cache
    if _explainer_cache is None:
        _explainer_cache = shap.TreeExplainer(model)
    return _explainer_cache


def explain_row(model, feature_row: pd.Series, predicted_label: str) -> list[dict]:
    """
    Return top-3 SHAP contributions for a single feature vector.

    Each entry: {"feature": str, "value": float, "shap": float, "direction": "↑"|"↓"}
    """
    explainer = get_explainer(model)
    X = pd.DataFrame([feature_row[FEATURE_COLUMNS]])

    sv = explainer.shap_values(X)
    classes = list(model.classes_)

    # SHAP >= 0.46 may return a 3-D ndarray (n_samples, n_features, n_classes)
    # instead of a list of (n_samples, n_features) arrays.
    if isinstance(sv, np.ndarray) and sv.ndim == 3:
        # shape: (n_samples, n_features, n_classes)
        class_idx = classes.index(predicted_label) if predicted_label in classes else 0
        contributions = sv[0, :, class_idx]  # (n_features,)
    elif isinstance(sv, list):
        # Legacy format: list of (n_samples, n_features) arrays, one per class
        class_idx = classes.index(predicted_label) if predicted_label in classes else 0
        arr = sv[class_idx]
        contributions = arr[0] if arr.ndim == 2 else arr
    else:
        contributions = np.zeros(len(FEATURE_COLUMNS))

    result = []
    for feat, feat_val, shap_val in zip(FEATURE_COLUMNS, X.iloc[0], contributions):
        result.append({
            "feature": feat,
            "value": float(feat_val),
            "shap": round(float(shap_val), 4),
            "direction": "↑" if shap_val > 0 else "↓",
        })

    result.sort(key=lambda x: abs(x["shap"]), reverse=True)
    return result[:3]


def store_explanation(ip: str, timestamp: str, label: str, shap_top3: list[dict]):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    record = {"ip": ip, "timestamp": timestamp, "label": label, "shap_top3": shap_top3}
    with _SHAP_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_explanation(ip: str, timestamp: str | None = None) -> dict | None:
    """Return the most recent SHAP record for an IP (optionally matching timestamp)."""
    if not _SHAP_FILE.exists():
        return None
    match = None
    with _SHAP_FILE.open() as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("ip") == ip:
                if timestamp is None or rec.get("timestamp") == timestamp:
                    match = rec   # keep last match
    return match
