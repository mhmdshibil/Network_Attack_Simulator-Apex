from backend.app.ml.dataset_generator import generate_dataset
from backend.app.core.paths import TRAINING_DATASET_PATH


def build(samples_per_class: int = 1000):
    TRAINING_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = generate_dataset(samples_per_class=samples_per_class)
    df.to_csv(TRAINING_DATASET_PATH, index=False)
    print(f"[OK] Dataset saved: {TRAINING_DATASET_PATH}  ({len(df)} rows, {df['label'].nunique()} classes)")
    print(df["label"].value_counts().to_string())


if __name__ == "__main__":
    build()
