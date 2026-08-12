import random
import pandas as pd
from backend.app.ml.attack_taxonomy import ATTACK_CLASSES
from backend.app.ml.feature_engineering import FEATURE_COLUMNS


def generate_samples(label: str, n: int) -> list[dict]:
    cfg = ATTACK_CLASSES[label]
    rows = []
    for _ in range(n):
        row = {col: _sample(cfg[col]) for col in FEATURE_COLUMNS}
        row["label"] = label
        rows.append(row)
    return rows


def _sample(rng):
    lo, hi = rng
    if isinstance(lo, float) or isinstance(hi, float):
        return round(random.uniform(lo, hi), 2)
    return random.randint(int(lo), int(hi))


def generate_dataset(samples_per_class: int = 1000) -> pd.DataFrame:
    rows = []
    for label in ATTACK_CLASSES:
        rows.extend(generate_samples(label, samples_per_class))
    return pd.DataFrame(rows)
