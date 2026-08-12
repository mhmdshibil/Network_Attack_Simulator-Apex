import joblib
from sklearn.ensemble import RandomForestClassifier

from backend.app.core.paths import RF_MODEL_PATH


def load_model() -> RandomForestClassifier:
    return joblib.load(RF_MODEL_PATH)


def predict(model, X):
    return model.predict(X)


def predict_proba(model, X):
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)
    return None


def train_model(X_train, y_train) -> RandomForestClassifier:
    model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    return model
