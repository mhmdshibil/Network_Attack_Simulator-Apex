# train_model.py
# This file contains the script for training the machine learning model.

import pandas as pd
import joblib
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from backend.app.ml.feature_engineering import FEATURE_COLUMNS

# Define the base directory and paths for the data and model.
BASE_DIR = Path(__file__).resolve().parents[3]

DATA_PATH = BASE_DIR / "data/processed/aggregated_traffic.csv"
MODEL_PATH = BASE_DIR / "models/random_forest.pkl"


def train_random_forest():
    """
    Train a RandomForestClassifier model and save it to a file.
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
    # Train the model when the script is executed directly.
    train_random_forest()