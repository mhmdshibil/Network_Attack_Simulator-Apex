# feature_engineering.py
# This file contains functions for loading and preparing data for machine learning models.

import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# A list of the feature columns to be used for model training.
FEATURE_COLUMNS = [
    "packets_per_second",
    "avg_request_rate",
    "failed_connections",
    "unique_ports"
]

def load_aggregated_data(path: str) -> pd.DataFrame:
    """
    Load aggregated traffic data from a CSV file.
    """
    return pd.read_csv(path)

def prepare_features(df: pd.DataFrame):
    """
    Prepare the features and labels for model training.
    """
    # Select the feature columns and the target label.
    X = df[FEATURE_COLUMNS]
    y = df["label"]

    # Scale the features using StandardScaler.
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Return the scaled features, labels, and the scaler object.
    return X_scaled, y, scaler