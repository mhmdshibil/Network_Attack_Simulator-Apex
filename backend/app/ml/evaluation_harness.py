"""
Evaluation harness — Phase 7.

Runs the full RF + IF pipeline against a held-out test set.
Reports precision, recall, F1, and false-positive rate per class,
then compares against a naive threshold baseline.

Usage:
    python -m backend.app.ml.evaluation_harness
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backend.app.ml.dataset_generator import generate_dataset
from backend.app.ml.model_utils import load_model, predict
from backend.app.ml.anomaly_model import load_anomaly_model, is_anomalous
from backend.app.ml.feature_engineering import FEATURE_COLUMNS


# ── Naive baseline classifier ──────────────────────────────────────────────────
def _baseline_predict(X: pd.DataFrame) -> np.ndarray:
    """
    Static threshold rules — no ML.
    Mirrors old-school IDS signatures on the 4 canonical features.
    """
    preds = []
    for _, row in X.iterrows():
        pps = row["packets_per_second"]
        arr = row["avg_request_rate"]
        fc  = row["failed_connections"]
        up  = row["unique_ports"]

        if up > 15:
            preds.append("port_scan")
        elif pps > 300:
            preds.append("ddos")
        elif fc > 7 and up <= 2:
            preds.append("bruteforce")
        elif pps > 30 and up > 2:
            preds.append("malware")
        elif fc > 0 and arr > 2:
            preds.append("sql_injection")
        else:
            preds.append("normal")
    return np.array(preds)


def _false_positive_rate(y_true, y_pred, label):
    """FPR = FP / (FP + TN) for one class (one-vs-rest)."""
    tp = ((y_pred == label) & (y_true == label)).sum()
    fp = ((y_pred == label) & (y_true != label)).sum()
    tn = ((y_pred != label) & (y_true != label)).sum()
    fn = ((y_pred != label) & (y_true == label)).sum()
    denom = fp + tn
    return fp / denom if denom > 0 else 0.0


def _metrics_table(y_true, y_pred, classes) -> pd.DataFrame:
    report = classification_report(y_true, y_pred, labels=classes, output_dict=True, zero_division=0)
    rows = []
    for cls in classes:
        r = report.get(cls, {})
        rows.append({
            "Class": cls,
            "Precision": round(r.get("precision", 0), 3),
            "Recall": round(r.get("recall", 0), 3),
            "F1": round(r.get("f1-score", 0), 3),
            "FPR": round(_false_positive_rate(y_true, y_pred, cls), 3),
            "Support": int(r.get("support", 0)),
        })
    return pd.DataFrame(rows)


def run_evaluation(samples_per_class: int = 500):
    print("Generating held-out evaluation dataset …")
    df = generate_dataset(samples_per_class=samples_per_class)
    X = df[FEATURE_COLUMNS]
    y = df["label"]
    classes = sorted(y.unique())

    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.30, random_state=99, stratify=y
    )
    y_test = y_test.reset_index(drop=True)
    X_test = X_test.reset_index(drop=True)

    # ── Random Forest ──────────────────────────────────────────────────────────
    model = load_model()
    rf_preds = predict(model, X_test)

    # ── Isolation Forest (zero-day layer) ─────────────────────────────────────
    anom_model = load_anomaly_model()
    anomalous = is_anomalous(anom_model, X_test)

    # Combined: RF says normal + IF says anomalous → "unknown_anomaly"
    combined_preds = rf_preds.copy()
    zero_day_mask = (rf_preds == "normal") & anomalous
    combined_preds[zero_day_mask] = "unknown_anomaly"

    # ── Baseline ───────────────────────────────────────────────────────────────
    baseline_preds = _baseline_predict(X_test)

    # ── Tables ─────────────────────────────────────────────────────────────────
    rf_table = _metrics_table(y_test, rf_preds, classes)
    baseline_table = _metrics_table(y_test, baseline_preds, classes)

    # IF coverage: what % of attack rows (non-normal) does IF flag?
    attack_mask = y_test != "normal"
    if_attack_caught = anomalous[attack_mask].sum()
    if_attack_total  = attack_mask.sum()
    if_normal_fp     = anomalous[~attack_mask].sum()
    if_normal_total  = (~attack_mask).sum()

    # ── Print markdown tables ──────────────────────────────────────────────────
    def _md_table(df: pd.DataFrame, title: str):
        print(f"\n### {title}\n")
        cols = df.columns.tolist()
        print("| " + " | ".join(cols) + " |")
        print("|" + "|".join(["-" * (len(c) + 2) for c in cols]) + "|")
        for _, row in df.iterrows():
            print("| " + " | ".join(str(row[c]) for c in cols) + " |")

    print("\n" + "=" * 70)
    print("NETWORK ATTACK SIMULATOR v2 — EVALUATION REPORT")
    print("=" * 70)

    _md_table(rf_table, "Random Forest Classifier (test set)")
    _md_table(baseline_table, "Naive Threshold Baseline (same test set)")

    print(f"""
### Isolation Forest — Zero-Day Coverage

| Metric | Value |
|---|---|
| Attack rows caught by IF | {if_attack_caught}/{if_attack_total} ({if_attack_caught/if_attack_total:.1%}) |
| Normal rows falsely flagged | {if_normal_fp}/{if_normal_total} ({if_normal_fp/if_normal_total:.1%}) |
| Zero-day rows injected | {zero_day_mask.sum()} |
""")

    rf_acc = (rf_preds == y_test).mean()
    bl_acc = (baseline_preds == y_test).mean()
    print(f"""
### Summary

| Model | Overall Accuracy |
|---|---|
| Random Forest | {rf_acc:.3f} |
| Naive Baseline | {bl_acc:.3f} |
| Δ improvement | +{rf_acc - bl_acc:.3f} |
""")

    return {
        "rf_table": rf_table,
        "baseline_table": baseline_table,
        "rf_accuracy": rf_acc,
        "baseline_accuracy": bl_acc,
    }


if __name__ == "__main__":
    run_evaluation()
