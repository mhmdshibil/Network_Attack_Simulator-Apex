# paths.py
# This file defines the directory and file paths used throughout the application.
# Using a centralized paths file makes it easier to manage file locations.

from pathlib import Path

# BASE_DIR is the root directory of the project.
# It is determined by going up three levels from the current file's location.
BASE_DIR = Path(__file__).resolve().parents[3]

# DATA_DIR is the directory where the application's data is stored.
DATA_DIR = BASE_DIR / "data"

# PROCESSED_DIR is the directory for storing processed data files.
PROCESSED_DIR = DATA_DIR / "processed"

# DETECTIONS_FILE is the path to the CSV file where attack detections are logged.
DETECTIONS_FILE = PROCESSED_DIR / "detections.csv"

# AGGREGATED_FILE is the path to the CSV file for aggregated traffic data.
AGGREGATED_FILE = PROCESSED_DIR / "aggregated_traffic.csv"