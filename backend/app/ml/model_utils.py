# model_utils.py
# This file contains utility functions for loading and using machine learning models.

import joblib
import numpy as np
from pathlib import Path

# Define the base directory and the path to the trained model.
BASE_DIR = Path(__file__).resolve().parents[3]
MODEL_PATH = BASE_DIR / "models/random_forest.pkl"


def load_model():
    """
    Load the trained machine learning model from the specified path.
    """
    return joblib.load(MODEL_PATH)


def predict(model, X):
    """
    Make predictions using the loaded model.
    """
    return model.predict(X)


def predict_proba(model, X):
    """
    Get the probability estimates for predictions.
    Returns None if the model does not support probability estimates.
    """
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)
    return None