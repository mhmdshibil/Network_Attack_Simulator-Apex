# log_service.py
# This file contains functions for loading and processing log data.

import pandas as pd
from pathlib import Path

# Define the directory where the raw log files are stored.
RAW_DIR = Path("data/raw")

def load_all_logs() -> pd.DataFrame:
    """
    Load all log files from the raw data directory and concatenate them into a single DataFrame.
    """
    frames = []
    # Iterate over all CSV files in the raw data directory.
    for file in RAW_DIR.glob("*.csv"):
        frames.append(pd.read_csv(file))
    # Concatenate all the DataFrames into a single one.
    return pd.concat(frames, ignore_index=True)


def aggregate_by_time_window(df: pd.DataFrame, window_seconds: int = 5) -> pd.DataFrame:
    """
    Aggregate the log data into time windows.
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