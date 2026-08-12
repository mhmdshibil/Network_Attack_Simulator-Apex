# Feature ranges expressed in terms of what aggregate_by_time_window() produces
# for a 5-second window. Each key matches FEATURE_COLUMNS exactly.
#
# packets_per_second  = sum(packet_count) per window
# avg_request_rate    = mean(request_rate) per window
# failed_connections  = count(success_flag == False) per window
# unique_ports        = nunique(destination_port) per window
#
# Ranges intentionally overlap between classes to produce realistic,
# non-trivial F1 scores when trained + evaluated. The hard distinguishing
# signal comes from the combination of features, not any single axis.

ATTACK_CLASSES = {
    "normal": {
        "packets_per_second": (1, 45),       # bursty browsing reaches ~45 pps
        "avg_request_rate": (0.5, 3.5),      # includes CDN and keep-alive chatter
        "failed_connections": (0, 3),         # HTTP 4xx / TLS renegotiations happen
        "unique_ports": (1, 4),              # multi-tab sessions use 2-4 ports
    },
    "port_scan": {
        "packets_per_second": (20, 120),     # low-speed scans overlap malware/bruteforce
        "avg_request_rate": (8.0, 40.0),
        "failed_connections": (10, 40),       # most probes are refused
        "unique_ports": (15, 100),           # key distinguisher
    },
    "ddos": {
        "packets_per_second": (120, 3000),   # lower end overlaps heavy legitimate traffic
        "avg_request_rate": (30.0, 500.0),
        "failed_connections": (0, 18),        # amplification attacks rarely fail
        "unique_ports": (1, 4),              # targets a single service
    },
    "bruteforce": {
        "packets_per_second": (5, 55),       # low-speed bruteforce overlaps normal
        "avg_request_rate": (0.8, 6.0),      # overlaps normal on the low end
        "failed_connections": (4, 50),        # key distinguisher — many auth failures
        "unique_ports": (1, 3),              # targets one or two services
    },
    "sql_injection": {
        "packets_per_second": (2, 30),       # heavy overlap with normal
        "avg_request_rate": (1.5, 9.0),      # overlaps normal
        "failed_connections": (0, 6),         # some injections succeed — low failures
        "unique_ports": (1, 3),              # targets the web app port
    },
    "malware": {
        "packets_per_second": (8, 300),      # slow C2 beaconing overlaps normal
        "avg_request_rate": (1.0, 50.0),     # wide range: slow C2 → active exfil
        "failed_connections": (0, 8),         # C2 channels usually stay connected
        "unique_ports": (1, 12),             # varies: single C2 port → spread
    },
}
