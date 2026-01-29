import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

FEATURE_COLUMNS = [
    "packets_per_second",
    "avg_request_rate",
    "failed_connections",
    "unique_ports"
]

def load_aggregated_data(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

def prepare_features(df: pd.DataFrame):
    X = df[FEATURE_COLUMNS]
    y = df["label"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, y, scaler