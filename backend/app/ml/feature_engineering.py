import pandas as pd

# Canonical feature set — must match what aggregate_by_time_window() produces
# and what attack_taxonomy.py / dataset_generator.py emit for training data.
FEATURE_COLUMNS = [
    "packets_per_second",
    "avg_request_rate",
    "failed_connections",
    "unique_ports",
]


def load_aggregated_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def prepare_features(df: pd.DataFrame):
    X = df[FEATURE_COLUMNS]
    y = df["label"]
    return X, y
