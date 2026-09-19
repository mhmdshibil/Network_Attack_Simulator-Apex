"""SHAP explainability endpoint — Phase 5."""
import json
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.ml.shap_explainer import load_explanation
from backend.app.ml.feature_engineering import FEATURE_COLUMNS
from backend.app.core.auth import require_analyst
from backend.app.core.paths import PROCESSED_DIR

router = APIRouter(prefix="/api/explain", tags=["explainability"])


@router.get("/")
def explain(ip: str = Query(...), ts: str | None = Query(None), _: dict = Depends(require_analyst)):
    """
    Return the SHAP explanation for the most recent detection from an IP.
    Optionally filter by exact timestamp (ts).
    """
    record = load_explanation(ip, timestamp=ts)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No SHAP explanation found for IP {ip}"
        )
    return record


@router.get("/summary")
def explain_summary(_: dict = Depends(require_analyst)):
    """
    Aggregate SHAP feature importance across all stored explanations, supplemented
    by the RF model's built-in Gini feature importances for completeness.
    """
    # ── RF Gini importances (all 7 features, authoritative global ranking) ─────
    try:
        import joblib
        from backend.app.core.paths import RF_MODEL_PATH
        rf = joblib.load(RF_MODEL_PATH)
        rf_importances = {
            feat: round(float(imp), 4)
            for feat, imp in zip(FEATURE_COLUMNS, rf.feature_importances_)
        }
    except Exception:
        rf_importances = {feat: 0.0 for feat in FEATURE_COLUMNS}

    # Build ranked list sorted by importance descending
    feature_importance = sorted(
        [{"feature": f, "importance": v} for f, v in rf_importances.items()],
        key=lambda x: -x["importance"],
    )
    for i, item in enumerate(feature_importance):
        item["rank"] = i + 1

    # ── SHAP aggregation — per-class top features from stored explanations ─────
    shap_file = PROCESSED_DIR / "shap_explanations.jsonl"
    feat_shap: dict = defaultdict(list)
    class_feat_shap: dict = defaultdict(lambda: defaultdict(list))
    total = 0

    if shap_file.exists():
        with shap_file.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    label = rec.get("label", "unknown")
                    for entry in rec.get("shap_top3", []):
                        feat = entry.get("feature")
                        val = abs(float(entry.get("shap", 0)))
                        if feat:
                            feat_shap[feat].append(val)
                            class_feat_shap[label][feat].append(val)
                    total += 1
                except Exception:
                    pass

    # Mean |SHAP| per feature
    mean_shap = {
        feat: round(sum(vals) / len(vals), 4) if vals else 0.0
        for feat, vals in feat_shap.items()
    }
    for item in feature_importance:
        item["mean_shap"] = mean_shap.get(item["feature"], 0.0)

    # Per-class top-2 features by mean |SHAP|
    per_class_top_features: dict = {}
    for cls, fd in class_feat_shap.items():
        sorted_feats = sorted(
            fd.items(),
            key=lambda x: -(sum(x[1]) / len(x[1]) if x[1] else 0),
        )
        per_class_top_features[cls] = [f[0] for f in sorted_feats[:2]]

    return {
        "feature_importance": feature_importance,
        "per_class_top_features": per_class_top_features,
        "total_explanations": total,
        "model_version": "v2",
        "feature_columns": FEATURE_COLUMNS,
    }
