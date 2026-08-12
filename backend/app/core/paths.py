# backend/app/core/paths.py
# This module centralizes all major file and directory paths used throughout the application.
# By defining these paths in one place, the codebase becomes more maintainable and less prone to
# errors from hardcoded or inconsistent file paths. It uses Python's `pathlib` for robust and
# platform-agnostic path manipulation. All paths are constructed relative to the project's
# base directory, ensuring that the application will work correctly regardless of where it is run.

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
POLICIES_DIR = DATA_DIR / "policies"
AUDIT_DIR = DATA_DIR / "audit"
TRAINING_DIR = DATA_DIR / "training"

# --- detection output ---
DETECTIONS_FILE = PROCESSED_DIR / "detections.csv"
AGGREGATED_FILE = PROCESSED_DIR / "aggregated_traffic.csv"

# --- policy state (canonical single location for all modules) ---
HARD_BLOCKED_IPS_FILE = POLICIES_DIR / "hard_blocked_ips.json"
REPUTATION_FILE = POLICIES_DIR / "ip_reputation.json"
LAST_SEEN_FILE = POLICIES_DIR / "ip_last_seen.json"
WHITELIST_FILE = POLICIES_DIR / "whitelist_ips.json"

# --- audit logs ---
AUDIT_EVENTS_FILE = AUDIT_DIR / "security_events.jsonl"
DECISION_AUDIT_FILE = AUDIT_DIR / "decision_audit.csv"

# --- ML models ---
MODELS_DIR = BASE_DIR / "models"
RF_MODEL_PATH = MODELS_DIR / "random_forest.pkl"
ANOMALY_MODEL_PATH = MODELS_DIR / "isolation_forest.pkl"
TRAINING_DATASET_PATH = TRAINING_DIR / "attack_dataset.csv"