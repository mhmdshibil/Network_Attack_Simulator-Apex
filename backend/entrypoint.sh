#!/bin/bash
set -e

echo "[apex] Checking ML models..."

# Train RF model if missing
if [ ! -f "models/random_forest.pkl" ]; then
  echo "[apex] Training Random Forest model..."
  python -m backend.app.ml.build_dataset
  python -m backend.app.ml.train_model
  echo "[apex] RF model ready."
fi

# Train Isolation Forest model if missing
if [ ! -f "models/isolation_forest.pkl" ]; then
  echo "[apex] Training Isolation Forest model..."
  python -c "from backend.app.ml.anomaly_model import train_isolation_forest; train_isolation_forest(); print('[apex] IF model ready.')"
fi

echo "[apex] Starting API server..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
