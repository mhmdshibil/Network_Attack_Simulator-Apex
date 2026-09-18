"""
CollegeNetworkProfile — a realistic college-network traffic profile.

This is additive: it plugs into auto_attack.py when TRAFFIC_PROFILE=college and
does not alter the default synthetic behavior. generate_window() returns rows in
the same schema as the generators in scripts/, with one extra trailing column —
target_zone — that NetworkMap.jsx uses to highlight the correct zone.

Row schema (see CollegeNetworkProfile.TRAFFIC_HEADER):
  timestamp, source_ip, destination_ip, destination_port, protocol,
  packet_count, request_rate, success_flag, label, target_zone

Behavior by time of day (datetime.now().hour):
  Peak      (08:00–22:00): high volume, 15% attack chance, mostly student IPs
  Off-peak  (22:00–08:00): low volume,  5% attack chance, mostly server IPs
"""
import random
from datetime import datetime, timedelta

# Internal zones — target_zone id → subnet octet + representative host.
# ids match ZONES in frontend/src/pages/NetworkMap.jsx.
ZONES = {
    "admin":        {"octet": 1, "host": "10.0.1.10"},
    "student_wifi": {"octet": 2, "host": "10.0.2.1"},
    "server_room":  {"octet": 3, "host": "10.0.3.10"},
    "lab":          {"octet": 4, "host": "10.0.4.10"},
}

# Public octet prefixes used for external attackers.
_EXTERNAL_PREFIXES = [185, 45, 103, 91]

# Weighted attack mix (must sum to 100).
_ATTACK_MIX = {
    "port_scan": 35,
    "bruteforce": 30,
    "ddos": 15,
    "sql_injection": 15,
    "malware": 5,
}

# Zones an external attacker is most likely to target (servers/admin over labs).
_TARGET_WEIGHTS = {"server_room": 40, "admin": 30, "student_wifi": 20, "lab": 10}

PEAK_START_HOUR = 8
PEAK_END_HOUR = 22


class CollegeNetworkProfile:
    """Generates one traffic window shaped like a real campus network."""

    TRAFFIC_HEADER = [
        "timestamp", "source_ip", "destination_ip", "destination_port",
        "protocol", "packet_count", "request_rate", "success_flag", "label",
        "target_zone",
    ]

    def __init__(self, now_provider=datetime.now):
        # now_provider is injectable for testing time-based behavior.
        self._now = now_provider

    # ── Time-of-day ─────────────────────────────────────────────────────────
    def is_peak(self) -> bool:
        return PEAK_START_HOUR <= self._now().hour < PEAK_END_HOUR

    def attack_probability(self) -> float:
        return 0.15 if self.is_peak() else 0.05

    # ── IP helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _internal_ip(octet: int) -> str:
        return f"10.0.{octet}.{random.randint(2, 254)}"

    @staticmethod
    def _external_ip() -> str:
        p = random.choice(_EXTERNAL_PREFIXES)
        return f"{p}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"

    def _normal_source(self) -> tuple:
        """Return (source_ip, zone_id) for a normal-traffic row."""
        # During peak, most traffic is students; off-peak, servers dominate.
        if self.is_peak():
            zone = random.choices(
                list(ZONES), weights=[10, 60, 20, 10], k=1
            )[0]
        else:
            zone = random.choices(
                list(ZONES), weights=[10, 15, 60, 15], k=1
            )[0]
        return self._internal_ip(ZONES[zone]["octet"]), zone

    @staticmethod
    def _pick_attack() -> str:
        types = list(_ATTACK_MIX.keys())
        weights = list(_ATTACK_MIX.values())
        return random.choices(types, weights=weights, k=1)[0]

    @staticmethod
    def _pick_target_zone() -> str:
        zones = list(_TARGET_WEIGHTS.keys())
        weights = list(_TARGET_WEIGHTS.values())
        return random.choices(zones, weights=weights, k=1)[0]

    # ── Row builders ────────────────────────────────────────────────────────
    def _normal_rows(self, start: datetime, n: int) -> list:
        rows = []
        for i in range(n):
            src, zone = self._normal_source()
            rows.append([
                (start + timedelta(seconds=i % 5, milliseconds=i)).isoformat(),
                src,
                ZONES[zone]["host"],
                random.choice([80, 443, 53]),
                random.choice(["HTTP", "HTTPS", "DNS"]),
                random.randint(1, 5),
                round(random.uniform(0.5, 2.0), 2),
                True,
                "normal",
                zone,
            ])
        return rows

    def _attack_rows(self, start: datetime, label: str) -> list:
        """Build a burst of rows for one attack, targeting one zone."""
        target_zone = self._pick_target_zone()
        dest = ZONES[target_zone]["host"]
        # Most external campaigns come from public IPs; port scans can be insider.
        if label == "port_scan" and random.random() < 0.4:
            src = self._internal_ip(ZONES[target_zone]["octet"])
        else:
            src = self._external_ip()

        rows = []
        if label == "port_scan":
            for i, port in enumerate(range(20, 60)):
                rows.append([(start + timedelta(milliseconds=i * 50)).isoformat(),
                             src, dest, port, "TCP",
                             random.randint(1, 3), round(random.uniform(20.0, 40.0), 2),
                             False, label, target_zone])
        elif label == "bruteforce":
            for i in range(25):
                rows.append([(start + timedelta(seconds=i % 5)).isoformat(),
                             src, dest, 22, "TCP",
                             random.randint(1, 3), round(random.uniform(1.0, 5.0), 2),
                             False, label, target_zone])
        elif label == "ddos":
            for i in range(40):
                rows.append([(start + timedelta(milliseconds=i * 5)).isoformat(),
                             src, dest, 80, "UDP",
                             random.randint(50, 200), round(random.uniform(100.0, 500.0), 2),
                             random.choice([True, True, False]), label, target_zone])
        elif label == "sql_injection":
            for i in range(15):
                rows.append([(start + timedelta(milliseconds=i * 250)).isoformat(),
                             src, dest, 80, "HTTP",
                             random.randint(1, 3), round(random.uniform(2.0, 8.0), 2),
                             random.choice([True, False, False]), label, target_zone])
        else:  # malware
            for i in range(20):
                rows.append([(start + timedelta(milliseconds=i * 25)).isoformat(),
                             src, dest, random.choice([443, 8080, 4444, 6667, 1337]), "TCP",
                             random.randint(5, 30), round(random.uniform(5.0, 50.0), 2),
                             random.choice([True, True, True, False]), label, target_zone])
        return rows

    # ── Public API ──────────────────────────────────────────────────────────
    def generate_window(self) -> list:
        """
        Return one window of rows (list of lists) in TRAFFIC_HEADER order.
        Includes normal traffic plus — with attack_probability — one attack burst.
        """
        start = self._now()
        normal_n = random.randint(50, 80) if self.is_peak() else random.randint(10, 25)
        rows = self._normal_rows(start, normal_n)

        if random.random() < self.attack_probability():
            rows += self._attack_rows(start, self._pick_attack())

        return rows


if __name__ == "__main__":
    import csv
    import os

    profile = CollegeNetworkProfile()
    os.makedirs("data/raw", exist_ok=True)
    window = profile.generate_window()
    with open("data/raw/college_traffic.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CollegeNetworkProfile.TRAFFIC_HEADER)
        w.writerows(window)
    print(f"College window generated — peak={profile.is_peak()}, rows={len(window)}")
