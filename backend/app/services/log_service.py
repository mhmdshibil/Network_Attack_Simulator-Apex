import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw")

def load_all_logs() -> pd.DataFrame:
    frames = []
    for file in RAW_DIR.glob("*.csv"):
        frames.append(pd.read_csv(file))
    return pd.concat(frames, ignore_index=True)


def aggregate_by_time_window(df: pd.DataFrame, window_seconds: int = 5) -> pd.DataFrame:
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    df.set_index("timestamp", inplace=True)

    agg = df.groupby(
        [pd.Grouper(freq=f"{window_seconds}s"), "source_ip"]
    ).agg(
        packets_per_second=("packet_count", "sum"),
        avg_request_rate=("request_rate", "mean"),
        failed_connections=("success_flag", lambda x: (~x).sum()),
        unique_ports=("destination_port", "nunique"),
        label=("label", "first")
    ).reset_index()

    return agg