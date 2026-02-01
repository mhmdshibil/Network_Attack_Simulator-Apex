import random
import pandas as pd
from backend.app.ml.attack_taxonomy import ATTACK_CLASSES

def generate_samples(label: str, n: int):
    cfg = ATTACK_CLASSES[label]
    rows = []

    for _ in range(n):
        rows.append({
            "packet_rate": random.randint(*cfg["packet_rate"]),
            "bytes_sent": random.randint(*cfg["bytes_sent"]),
            "unique_ports": random.randint(*cfg["unique_ports"]),
            "failed_logins": random.randint(*cfg["failed_logins"]),
            "label": label,
        })

    return rows

def generate_dataset(samples_per_class=1000):
    data = []
    for label in ATTACK_CLASSES:
        data.extend(generate_samples(label, samples_per_class))
    return pd.DataFrame(data)