import random
import pandas as pd
from backend.app.ml.attack_taxonomy import ATTACK_CLASSES
from backend.app.ml.feature_engineering import FEATURE_COLUMNS

# Gaussian noise applied after uniform sampling — 10% of each feature's range
# as std dev. This prevents the RF from learning perfect box boundaries.
_NOISE_STD_FRAC = 0.10


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
    is_float = isinstance(lo, float) or isinstance(hi, float)
    val = random.uniform(lo, hi) if is_float else float(random.randint(int(lo), int(hi)))
    # Add Gaussian jitter so samples cluster naturally rather than in hard boxes
    val += random.gauss(0, (hi - lo) * _NOISE_STD_FRAC)
    val = max(0.0, val)
    return round(val, 2) if is_float else int(round(val))


def generate_dataset(samples_per_class: int = 1000) -> pd.DataFrame:
    rows = []
    for label in ATTACK_CLASSES:
        rows.extend(generate_samples(label, samples_per_class))
    return pd.DataFrame(rows)
