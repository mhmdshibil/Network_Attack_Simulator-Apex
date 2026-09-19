"""Synthetic DDoS flood traffic generator."""
import random
from datetime import datetime, timedelta


def generate_ddos(n_packets: int = 200, target_ip: str = "192.168.1.10",
                  source_ip: str = "185.220.101.55") -> list:
    start = datetime.now()
    rows = []
    for i in range(n_packets):
        rows.append([
            (start + timedelta(milliseconds=i * 5)).isoformat(),
            source_ip,
            target_ip,
            80,
            "UDP",
            random.randint(50, 200),                      # high packet_count
            round(random.uniform(100.0, 500.0), 2),       # very high request_rate
            random.choice([True, True, False]),            # mostly succeed (volumetric)
            "ddos",
            round(random.uniform(500.0, 1500.0), 2),      # bytes_per_packet
            round(random.uniform(0.01, 0.1), 4),          # connection_duration
            round(random.uniform(0.5, 2.0), 2),           # payload_entropy
        ])
    return rows


if __name__ == "__main__":
    import csv, os
    os.makedirs("data/raw", exist_ok=True)
    with open("data/raw/ddos.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "source_ip", "destination_ip", "destination_port",
                    "protocol", "packet_count", "request_rate", "success_flag", "label",
                    "bytes_per_packet", "connection_duration", "payload_entropy"])
        w.writerows(generate_ddos())
    print("DDoS traffic generated.")
