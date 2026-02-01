# backend/app/ml/train_model.py
# This module contains the script responsible for training the machine learning model. It orchestrates
# the end-to-end training process, from loading the data to saving the final trained model. The script
# uses a RandomForestClassifier, a powerful ensemble model, and evaluates its performance using standard
# classification metrics. This centralized training script ensures that the model can be consistently
# and reproducibly trained and updated.

import pandas as pd
import joblib
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from backend.app.ml.feature_engineering import FEATURE_COLUMNS

# The base directory of the project, used to construct absolute paths to data and model files.
BASE_DIR = Path(__file__).resolve().parents[3]

# The path to the processed, aggregated traffic data used for training the model.
DATA_PATH = BASE_DIR / "data/processed/aggregated_traffic.csv"
# The path where the trained model will be saved.
MODEL_PATH = BASE_DIR / "models/random_forest.pkl"


def train_random_forest():
    """
    Trains a RandomForestClassifier model on the aggregated traffic data and saves it.

    This function performs the following steps:
    1. Loads the dataset from the specified `DATA_PATH`.
    2. Separates the data into features (X) and the target label (y).
    3. Splits the data into training and testing sets, using stratification to maintain the
       same proportion of labels in both sets.
    4. Initializes a `RandomForestClassifier` with 100 estimators.
    5. Trains the model using the training data.
    6. Evaluates the model's performance on the test data by printing a classification report
       and a confusion matrix.
    7. Serializes and saves the trained model to the `MODEL_PATH` using `joblib`.
    """
    # Load the aggregated traffic data.
    df = pd.read_csv(DATA_PATH)

    # Select the features and the target label.
    X = df[FEATURE_COLUMNS]
    y = df["label"]

    # Split the data into training and testing sets.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Initialize the RandomForestClassifier model.
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42
    )

    # Train the model on the training data.
    model.fit(X_train, y_train)

    # Make predictions on the test data.
    y_pred = model.predict(X_test)

    # Print the classification report and confusion matrix.
    print("Classification Report:")
    print(classification_report(y_test, y_pred))

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Save the trained model to a file.
    joblib.dump(model, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    # This block allows the script to be run directly from the command line to train the model.
    train_random_forest()