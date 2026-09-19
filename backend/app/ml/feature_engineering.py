import pandas as pd

# Canonical feature set — must match what aggregate_by_time_window() produces
# and what attack_taxonomy.py / dataset_generator.py emit for training data.
#
# v2 adds three new features:
#   bytes_per_packet   — average payload size; large = DDoS/exfil, small = scan
#   connection_duration — avg connection lifetime; short = probe, long = C2/DDoS
#   payload_entropy    — Shannon entropy of packet payload; high = encrypted C2
FEATURE_COLUMNS = [
    "packets_per_second",
    "avg_request_rate",
    "failed_connections",
    "unique_ports",
    "bytes_per_packet",
    "connection_duration",
    "payload_entropy",
]


def load_aggregated_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def prepare_features(df: pd.DataFrame):
    X = df[FEATURE_COLUMNS]
    y = df["label"]
    return X, y
