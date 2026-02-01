from backend.app.ml.dataset_generator import generate_dataset
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
DATASET_PATH = BASE_DIR / "data/training/attack_dataset.csv"

def build():
    df = generate_dataset(samples_per_class=1000)
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATASET_PATH, index=False)
    print(f"[OK] Dataset saved at {DATASET_PATH}")

if __name__ == "__main__":
    build()
