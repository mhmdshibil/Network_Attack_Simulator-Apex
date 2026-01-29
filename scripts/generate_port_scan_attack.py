# generate_port_scan_attack.py
# This script generates synthetic port scan attack data for testing purposes.

import csv
import random
from datetime import datetime, timedelta
import os

# Define the output file for the generated data.
OUTPUT_FILE = "data/raw/port_scan.csv"

def generate_port_scan(n_ports=80):
    """
    Generate a specified number of rows of port scan attack data.
    """
    start = datetime.now()
    rows = []

    source_ip = "10.0.0.99"
    dest_ip = "192.168.1.10"

    # Generate data for a scan of n_ports.
    for i, port in enumerate(range(20, 20 + n_ports)):
        rows.append([
            (start + timedelta(milliseconds=i * 50)).isoformat(),
            source_ip,
            dest_ip,
            port,  # The port being scanned.
            "TCP",
            random.randint(1, 3),  # Packet Count
            round(random.uniform(20.0, 40.0), 2),  # Request Rate
            False,  # Success Flag (most scans will fail)
            "port_scan"  # Label
        ])

    return rows

if __name__ == "__main__":
    # Ensure the output directory exists.
    os.makedirs("data/raw", exist_ok=True)

    # Open the output file in write mode.
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        # Write the header row.
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
        # Write the generated data to the file.
        writer.writerows(generate_port_scan())

    print("Port scan traffic generated.")