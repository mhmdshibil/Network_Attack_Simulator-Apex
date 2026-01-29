import csv
import random
from datetime import datetime, timedelta

OUTPUT_FILE = "data/raw/normal_traffic.csv"

def generate_normal_traffic(n=200):
    start = datetime.now()
    rows = []

    for i in range(n):
        rows.append([
            (start + timedelta(seconds=i)).isoformat(),
            f"10.0.0.{random.randint(2, 20)}",
            "192.168.1.10",
            80,
            "HTTP",
            random.randint(1, 5),
            round(random.uniform(0.5, 2.0), 2),
            True,
            "normal"
        ])

    return rows

if __name__ == "__main__":
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "source_ip",
            "destination_ip",
            "destination_port",
            "protocol",
            "packet_count",
            "request_rate",
            "success_flag",
            "label"
        ])
        writer.writerows(generate_normal_traffic())

    print("Normal traffic generated.")