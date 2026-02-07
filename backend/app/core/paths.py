# backend/app/core/paths.py
# This module centralizes all major file and directory paths used throughout the application.
# By defining these paths in one place, the codebase becomes more maintainable and less prone to
# errors from hardcoded or inconsistent file paths. It uses Python's `pathlib` for robust and
# platform-agnostic path manipulation. All paths are constructed relative to the project's
# base directory, ensuring that the application will work correctly regardless of where it is run.

from pathlib import Path

# `BASE_DIR` represents the absolute path to the root directory of the project. It is calculated
# by navigating three levels up from the current file's location (`.../app/core/paths.py`).
# This serves as the anchor for all other paths in the application.
BASE_DIR = Path(__file__).resolve().parents[3]

# `DATA_DIR` points to the primary directory for storing all application-related data,
# including raw datasets and processed outputs.
DATA_DIR = BASE_DIR / "data"

# `PROCESSED_DIR` is a subdirectory within `DATA_DIR` specifically for storing data files that
# have been cleaned, transformed, or otherwise processed by the application.
PROCESSED_DIR = DATA_DIR / "processed"

# `DETECTIONS_FILE` is the full path to the CSV file where all detected attack events are
# logged. This file is a critical source of data for the analytics and response engines.
DETECTIONS_FILE = PROCESSED_DIR / "detections.csv"

# `AGGREGATED_FILE` is the full path to the CSV file used for storing aggregated network
# traffic data. This can be used for performance monitoring or further analysis.
AGGREGATED_FILE = PROCESSED_DIR / "aggregated_traffic.csv"

# `POLICIES_DIR` points to the directory where policy-related files are stored.
POLICIES_DIR = DATA_DIR / "policies"

# `HARD_BLOCKED_IPS_FILE` is the full path to the JSON file that lists IP addresses
# that are permanently blocked by policy.
HARD_BLOCKED_IPS_FILE = POLICIES_DIR / "hard_blocked_ips.json"