import joblib
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
MODEL_PATH = BASE_DIR / "models/random_forest.pkl"


def load_model():
    return joblib.load(MODEL_PATH)


def predict(model, X):
    return model.predict(X)


def predict_proba(model, X):
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)
    return None