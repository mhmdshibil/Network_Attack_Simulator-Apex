import pandas as pd
from pathlib import Path
from sklearn.metrics import confusion_matrix, accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from backend.app.ml.model_utils import train_model
from backend.app.ml.feature_engineering import FEATURE_COLUMNS

BASE_DIR = Path(__file__).resolve().parents[3]
DATASET_PATH = BASE_DIR / "data/training/attack_dataset.csv"


def evaluate():
    if not DATASET_PATH.exists():
        raise FileNotFoundError("Training dataset not found")

    df = pd.read_csv(DATASET_PATH)

    X = df[FEATURE_COLUMNS]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    model = train_model(X_train, y_train)

    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred, labels=sorted(y.unique()))
    report = classification_report(y_test, y_pred)

    print("\n=== ACCURACY ===")
    print(acc)

    print("\n=== CONFUSION MATRIX ===")
    print(cm)

    print("\n=== CLASSIFICATION REPORT ===")
    print(report)


if __name__ == "__main__":
    evaluate()