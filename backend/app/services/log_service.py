# backend/app/services/log_service.py
# This module provides functions for loading and processing raw log data from the file system. It is a
# critical part of the data ingestion pipeline, responsible for reading log files, consolidating them,
# and aggregating the data into a format suitable for machine learning. The `aggregate_by_time_window`
# function is particularly important, as it transforms raw, event-level data into a time-series format
# with engineered features, which is essential for the detection engine.

import pandas as pd
from pathlib import Path

# The directory where the raw log files (in CSV format) are stored. The service reads all files
# from this directory to build a comprehensive dataset for analysis.
RAW_DIR = Path("data/raw")

def load_all_logs() -> pd.DataFrame:
    """
    Loads all log files from the `RAW_DIR`, concatenates them, and returns a single DataFrame.

    This function iterates through all CSV files in the raw data directory, reads each one into a
    pandas DataFrame, and then combines them into a single, unified DataFrame for processing.

    Returns:
        pd.DataFrame: A single DataFrame containing the data from all log files.
    """
    frames = []
    # Iterate over all CSV files in the raw data directory.
    for file in RAW_DIR.glob("*.csv"):
        frames.append(pd.read_csv(file))
    # Concatenate all the DataFrames into a single one.
    return pd.concat(frames, ignore_index=True)


def aggregate_by_time_window(df: pd.DataFrame, window_seconds: int = 5) -> pd.DataFrame:
    """
    Aggregates log data into fixed-size time windows and computes key features.

    This function takes a DataFrame of log data, groups it by source IP within specific time
    intervals (e.g., every 5 seconds), and then calculates a set of aggregated features for each
    group. These features are essential for the machine learning model and include:
    - `packets_per_second`: Total packets in the window.
    - `avg_request_rate`: Average request rate.
    - `failed_connections`: Count of unsuccessful connections.
    - `unique_ports`: Number of unique destination ports.

    Args:
        df (pd.DataFrame): The input DataFrame of raw log data.
        window_seconds (int, optional): The size of the time window in seconds for aggregation.
                                        Defaults to 5.

    Returns:
        pd.DataFrame: A new DataFrame with the aggregated features, indexed by time window and IP.
    """
    # Convert the timestamp column to datetime objects and sort the DataFrame.
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    # Set the timestamp as the index of the DataFrame.
    df.set_index("timestamp", inplace=True)

    # Group the data by time window and source IP, and aggregate the features.
    agg = df.groupby(
        [pd.Grouper(freq=f"{window_seconds}s"), "source_ip"]
    ).agg(
        packets_per_second=("packet_count", "sum"),
        avg_request_rate=("request_rate", "mean"),
        failed_connections=("success_flag", lambda x: (~x).sum()),
        unique_ports=("destination_port", "nunique"),
        label=("label", "first")
    ).reset_index()

    # Return the aggregated DataFrame.
    return agg