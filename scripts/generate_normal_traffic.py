# generate_normal_traffic.py
# This script generates synthetic normal network traffic data for testing purposes.

import csv
import random
from datetime import datetime, timedelta

# Define the output file for the generated data.
OUTPUT_FILE = "data/raw/normal_traffic.csv"

def generate_normal_traffic(n=200):
    """
    Generate a specified number of rows of normal traffic data.
    """
    start = datetime.now()
    rows = []

    # Generate n rows of data.
    for i in range(n):
        rows.append([
            (start + timedelta(seconds=i)).isoformat(),
            f"10.0.0.{random.randint(2, 20)}",  # Source IP
            "192.168.1.10",  # Destination IP
            80,  # Destination Port
            "HTTP",  # Protocol
            random.randint(1, 5),  # Packet Count
            round(random.uniform(0.5, 2.0), 2),  # Request Rate
            True,  # Success Flag
            "normal"  # Label
        ])

    return rows

if __name__ == "__main__":
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
        writer.writerows(generate_normal_traffic())

    print("Normal traffic generated.")