import csv
import random
from datetime import datetime, timedelta
import os

OUTPUT_FILE = "data/raw/port_scan.csv"

def generate_port_scan(n_ports=80):
    start = datetime.now()
    rows = []

    source_ip = "10.0.0.99"
    dest_ip = "192.168.1.10"

    for i, port in enumerate(range(20, 20 + n_ports)):
        rows.append([
            (start + timedelta(milliseconds=i * 50)).isoformat(),
            source_ip,
            dest_ip,
            port,
            "TCP",
            random.randint(1, 3),
            round(random.uniform(20.0, 40.0), 2),
            False,
            "port_scan"
        ])

    return rows

if __name__ == "__main__":
    os.makedirs("data/raw", exist_ok=True)

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
        writer.writerows(generate_port_scan())

    print("Port scan traffic generated.")