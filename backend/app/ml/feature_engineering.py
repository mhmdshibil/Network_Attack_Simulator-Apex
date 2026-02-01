# backend/app/ml/feature_engineering.py
# This module contains functions dedicated to loading and preparing data for use in machine learning
# models. Its responsibilities include loading aggregated traffic data from CSV files and transforming
# it into a suitable format for training. This involves selecting relevant feature columns, scaling
# numerical features to a standard range, and separating the features from the target labels.
# By centralizing these data preparation steps, the module ensures that the model receives consistent
# and well-formed input.

import pandas as pd
from sklearn.preprocessing import StandardScaler

# A list of the names of the feature columns that will be used for training the machine learning model.
# These features are selected from the aggregated traffic data and are considered to be the most
# indicative of the patterns the model should learn.
FEATURE_COLUMNS = [
    "packets_per_second",
    "avg_request_rate",
    "failed_connections",
    "unique_ports"
]

def load_aggregated_data(path: str) -> pd.DataFrame:
    """
    Loads aggregated traffic data from a specified CSV file into a pandas DataFrame.

    Args:
        path (str): The file path to the CSV containing the aggregated data.

    Returns:
        pd.DataFrame: A DataFrame with the loaded data.
    """
    return pd.read_csv(path)

def prepare_features(df: pd.DataFrame):
    """
    Prepares the features and labels from the raw DataFrame for model training.

    This function performs two key steps:
    1. It separates the DataFrame into features (X) and the target label (y). The features are
       selected based on the `FEATURE_COLUMNS` list.
    2. It applies standard scaling to the feature data. Scaling is a crucial preprocessing step
       that standardizes the range of the features, ensuring that each one contributes proportionally
       to the model's learning process.

    Args:
        df (pd.DataFrame): The input DataFrame containing both features and the target label.

    Returns:
        tuple: A tuple containing:
            - X_scaled (np.ndarray): The scaled feature data.
            - y (pd.Series): The target labels.
            - scaler (StandardScaler): The fitted scaler object, which can be saved and used
              later to scale new data for prediction.
    """
    # Select the feature columns and the target label.
    X = df[FEATURE_COLUMNS]
    y = df["label"]

    # Scale the features using StandardScaler.
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Return the scaled features, labels, and the scaler object.
    return X_scaled, y, scaler