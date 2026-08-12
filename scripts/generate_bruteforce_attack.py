"""Synthetic brute-force login traffic generator."""
import random
from datetime import datetime, timedelta


def generate_bruteforce(n_attempts: int = 60, target_ip: str = "192.168.1.10",
                         source_ip: str = "103.21.244.17") -> list:
    start = datetime.now()
    rows = []
    for i in range(n_attempts):
        rows.append([
            (start + timedelta(seconds=i)).isoformat(),
            source_ip,
            target_ip,
            22,                                  # SSH
            "TCP",
            random.randint(1, 3),
            round(random.uniform(1.0, 5.0), 2),
            False,                               # login fails
            "bruteforce",
        ])
    return rows


if __name__ == "__main__":
    import csv, os
    os.makedirs("data/raw", exist_ok=True)
    with open("data/raw/bruteforce.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "source_ip", "destination_ip", "destination_port",
                    "protocol", "packet_count", "request_rate", "success_flag", "label"])
        w.writerows(generate_bruteforce())
    print("Brute-force traffic generated.")
