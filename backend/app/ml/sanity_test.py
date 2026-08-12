"""
Sanity test — Phase 1.

Runs 20 known port_scan rows and 20 normal rows through the full
aggregation + RF + IF pipeline and prints predicted vs expected labels.
"""
import sys
import pandas as pd
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backend.app.ml.attack_taxonomy import ATTACK_CLASSES
from backend.app.ml.dataset_generator import generate_samples
from backend.app.ml.model_utils import load_model, predict, predict_proba
from backend.app.ml.anomaly_model import load_anomaly_model, is_anomalous
from backend.app.ml.feature_engineering import FEATURE_COLUMNS


def run_sanity_test(n: int = 20):
    model = load_model()
    anom_model = load_anomaly_model()

    results = []
    for label in ("port_scan", "normal", "ddos", "bruteforce", "sql_injection", "malware"):
        rows = generate_samples(label, n)
        df = pd.DataFrame(rows)
        X = df[FEATURE_COLUMNS]
        preds = predict(model, X)
        probas = predict_proba(model, X)
        anomalous = is_anomalous(anom_model, X)

        correct = (preds == label).sum()
        anom_caught = anomalous.sum()

        results.append({
            "true_label": label,
            "n_samples": n,
            "rf_correct": int(correct),
            "rf_accuracy": f"{correct/n:.0%}",
            "if_flagged": int(anom_caught),
        })

    print(f"\n{'Label':<16} {'RF Correct':>12} {'RF Acc':>8} {'IF Flagged':>12}")
    print("-" * 54)
    for r in results:
        print(
            f"{r['true_label']:<16} {r['rf_correct']:>12} "
            f"{r['rf_accuracy']:>8} {r['if_flagged']:>12}"
        )

    rf_overall = sum(r["rf_correct"] for r in results)
    total = sum(r["n_samples"] for r in results)
    print(f"\nOverall RF accuracy: {rf_overall}/{total} = {rf_overall/total:.1%}")
    return results


if __name__ == "__main__":
    run_sanity_test()
