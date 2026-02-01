# backend/app/ml/model_utils.py
# This module provides utility functions for loading and interacting with the trained machine
# learning model. It abstracts the underlying details of model serialization and prediction,
# offering a simple and consistent interface for other parts of the application. By centralizing
# these functions, the module makes it easy to manage the model's lifecycle, from loading it into
# memory to using it for predictions.

import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier

# The base directory of the project, calculated by navigating up from the current file's location.
# This ensures that file paths are resolved correctly, regardless of where the script is run.
BASE_DIR = Path(__file__).resolve().parents[3]

# The full path to the serialized, trained machine learning model. `joblib` is used for
# efficient serialization of Python objects, which is ideal for scikit-learn models.
MODEL_PATH = BASE_DIR / "models/random_forest.pkl"


def load_model():
    """
    Loads the trained machine learning model from the predefined `MODEL_PATH`.

    This function uses `joblib.load` to deserialize the model from disk and return it as a
    usable Python object.

    Returns:
        The deserialized machine learning model object.
    """
    return joblib.load(MODEL_PATH)


def predict(model, X):
    """
    Makes predictions on a given dataset using the provided model.

    Args:
        model: The trained machine learning model object.
        X (np.ndarray or pd.DataFrame): The input data (features) to make predictions on.

    Returns:
        np.ndarray: An array of predictions from the model.
    """
    return model.predict(X)


def predict_proba(model, X):
    """
    Gets the probability estimates for each class for a given dataset.

    This function checks if the model has a `predict_proba` method, which is common in
    classification models. If it exists, it returns the probability estimates. Otherwise, it
    returns `None`, providing a safe way to handle models that do not support this feature.

    Args:
        model: The trained machine learning model object.
        X (np.ndarray or pd.DataFrame): The input data (features).

    Returns:
        np.ndarray or None: An array of probability estimates for each class, or `None` if the
                            model does not support probability predictions.
    """
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)
    return None

def train_model(X_train, y_train):
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42
    )
    model.fit(X_train, y_train)
    return model