import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from backend.app.ml.feature_engineering import FEATURE_COLUMNS
from backend.app.core.paths import TRAINING_DATASET_PATH, RF_MODEL_PATH


def train_random_forest() -> RandomForestClassifier:
    if not TRAINING_DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found at {TRAINING_DATASET_PATH}. "
            "Run build_dataset.py first."
        )

    df = pd.read_csv(TRAINING_DATASET_PATH)
    X = df[FEATURE_COLUMNS]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("=== Classification Report ===")
    print(classification_report(y_test, y_pred))
    print("=== Confusion Matrix ===")
    print(confusion_matrix(y_test, y_pred, labels=sorted(y.unique())))

    RF_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, RF_MODEL_PATH)
    print(f"\n[OK] Model saved: {RF_MODEL_PATH}")
    return model


if __name__ == "__main__":
    train_random_forest()
