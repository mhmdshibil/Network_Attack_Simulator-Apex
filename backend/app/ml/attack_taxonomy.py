# Feature ranges expressed in terms of what aggregate_by_time_window() produces
# for a 5-second window. Each key matches FEATURE_COLUMNS exactly.
#
# packets_per_second   = sum(packet_count) per window
# avg_request_rate     = mean(request_rate) per window
# failed_connections   = count(success_flag == False) per window
# unique_ports         = nunique(destination_port) per window
# bytes_per_packet     = mean(bytes_per_packet) per window  [v2]
# connection_duration  = mean(connection_duration) per window  [v2, seconds]
# payload_entropy      = mean(payload_entropy) per window  [v2, bits 0–8]
#
# Ranges intentionally overlap between classes to produce realistic,
# non-trivial F1 scores when trained + evaluated. The hard distinguishing
# signal comes from the combination of features, not any single axis.
#
# v2 distinguishing logic:
#   port_scan:     tiny packets (probes), very short duration, low entropy
#   ddos:          large packets (flood), very short duration, very low entropy (repetitive)
#   bruteforce:    medium packets, short duration, medium-high entropy (credential data)
#   sql_injection: medium-large packets, medium duration, LOW entropy (structured SQL)
#   malware:       large packets, LONG duration, VERY HIGH entropy (encrypted C2)
#   normal:        medium packets, moderate duration, medium-high entropy

ATTACK_CLASSES = {
    "normal": {
        "packets_per_second": (1, 45),        # bursty browsing reaches ~45 pps
        "avg_request_rate": (0.5, 3.5),       # includes CDN and keep-alive chatter
        "failed_connections": (0, 3),          # HTTP 4xx / TLS renegotiations happen
        "unique_ports": (1, 4),               # multi-tab sessions use 2-4 ports
        "bytes_per_packet": (200.0, 600.0),   # mixed web content
        "connection_duration": (1.0, 10.0),   # typical HTTP/S session lifetimes
        "payload_entropy": (3.5, 6.0),        # web content is moderately entropic
    },
    "port_scan": {
        "packets_per_second": (20, 120),      # low-speed scans overlap malware/bruteforce
        "avg_request_rate": (8.0, 40.0),
        "failed_connections": (10, 40),        # most probes are refused
        "unique_ports": (15, 100),            # key distinguisher
        "bytes_per_packet": (40.0, 80.0),     # tiny probe packets
        "connection_duration": (0.1, 0.5),    # probes time out almost immediately
        "payload_entropy": (1.0, 3.0),        # minimal/no payload
    },
    "ddos": {
        "packets_per_second": (120, 3000),    # lower end overlaps heavy legitimate traffic
        "avg_request_rate": (30.0, 500.0),
        "failed_connections": (0, 18),         # amplification attacks rarely fail
        "unique_ports": (1, 4),               # targets a single service
        "bytes_per_packet": (500.0, 1500.0),  # large flood packets
        "connection_duration": (0.01, 0.1),   # stateless UDP floods
        "payload_entropy": (0.5, 2.0),        # highly repetitive fill bytes
    },
    "bruteforce": {
        "packets_per_second": (5, 55),        # low-speed bruteforce overlaps normal
        "avg_request_rate": (0.8, 6.0),       # overlaps normal on the low end
        "failed_connections": (4, 50),         # key distinguisher — many auth failures
        "unique_ports": (1, 3),               # targets one or two services
        "bytes_per_packet": (200.0, 400.0),   # credential request/response packets
        "connection_duration": (1.0, 3.0),    # short login sessions
        "payload_entropy": (3.0, 5.0),        # credential data has moderate entropy
    },
    "sql_injection": {
        "packets_per_second": (2, 30),        # heavy overlap with normal
        "avg_request_rate": (1.5, 9.0),       # overlaps normal
        "failed_connections": (0, 6),          # some injections succeed — low failures
        "unique_ports": (1, 3),               # targets the web app port
        "bytes_per_packet": (350.0, 900.0),   # SQL payloads are larger than normal GETs
        "connection_duration": (2.0, 8.0),    # interactive injection sessions
        "payload_entropy": (2.0, 3.5),        # structured SQL has LOW entropy
    },
    "malware": {
        "packets_per_second": (8, 300),       # slow C2 beaconing overlaps normal
        "avg_request_rate": (1.0, 50.0),      # wide range: slow C2 → active exfil
        "failed_connections": (0, 8),          # C2 channels usually stay connected
        "unique_ports": (1, 12),              # varies: single C2 port → spread
        "bytes_per_packet": (800.0, 2000.0),  # large encrypted exfil chunks
        "connection_duration": (5.0, 30.0),   # persistent C2 sessions
        "payload_entropy": (6.5, 8.0),        # encrypted traffic is near-random
    },
}
