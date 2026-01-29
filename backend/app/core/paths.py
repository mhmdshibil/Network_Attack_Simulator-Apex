from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

DETECTIONS_FILE = PROCESSED_DIR / "detections.csv"
AGGREGATED_FILE = PROCESSED_DIR / "aggregated_traffic.csv"