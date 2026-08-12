# Feature ranges expressed in terms of what aggregate_by_time_window() produces
# for a 5-second window. Each key matches FEATURE_COLUMNS exactly.
#
# packets_per_second  = sum(packet_count) per window
# avg_request_rate    = mean(request_rate) per window
# failed_connections  = count(success_flag == False) per window
# unique_ports        = nunique(destination_port) per window

ATTACK_CLASSES = {
    "normal": {
        "packets_per_second": (1, 25),   # 1 covers sparse single-IP windows
        "avg_request_rate": (0.5, 2.0),
        "failed_connections": (0, 1),
        "unique_ports": (1, 2),
    },
    "port_scan": {
        "packets_per_second": (40, 120),
        "avg_request_rate": (20.0, 40.0),
        "failed_connections": (15, 40),
        "unique_ports": (20, 100),
    },
    "ddos": {
        "packets_per_second": (500, 3000),
        "avg_request_rate": (100.0, 500.0),
        "failed_connections": (0, 10),
        "unique_ports": (1, 3),
    },
    "bruteforce": {
        "packets_per_second": (10, 50),
        "avg_request_rate": (1.0, 5.0),
        "failed_connections": (8, 50),
        "unique_ports": (1, 2),
    },
    "sql_injection": {
        "packets_per_second": (5, 20),
        "avg_request_rate": (2.0, 8.0),
        "failed_connections": (1, 5),
        "unique_ports": (1, 2),
    },
    "malware": {
        "packets_per_second": (50, 300),
        "avg_request_rate": (5.0, 50.0),
        "failed_connections": (0, 5),
        "unique_ports": (2, 10),
    },
}
