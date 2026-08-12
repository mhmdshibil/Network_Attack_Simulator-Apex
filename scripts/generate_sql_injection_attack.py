"""Synthetic SQL-injection HTTP traffic generator."""
import random
from datetime import datetime, timedelta


def generate_sql_injection(n_requests: int = 40, target_ip: str = "192.168.1.10",
                            source_ip: str = "146.70.29.83") -> list:
    start = datetime.now()
    rows = []
    for i in range(n_requests):
        rows.append([
            (start + timedelta(milliseconds=i * 250)).isoformat(),
            source_ip,
            target_ip,
            80,
            "HTTP",
            random.randint(1, 3),
            round(random.uniform(2.0, 8.0), 2),   # slightly elevated rate (automated tool)
            random.choice([True, False, False]),    # many fail (error responses)
            "sql_injection",
        ])
    return rows


if __name__ == "__main__":
    import csv, os
    os.makedirs("data/raw", exist_ok=True)
    with open("data/raw/sql_injection.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "source_ip", "destination_ip", "destination_port",
                    "protocol", "packet_count", "request_rate", "success_flag", "label"])
        w.writerows(generate_sql_injection())
    print("SQL injection traffic generated.")
