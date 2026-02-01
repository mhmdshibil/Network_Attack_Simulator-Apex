ATTACK_CLASSES = {
    "normal": {
        "packet_rate": (1, 5),
        "bytes_sent": (100, 500),
        "unique_ports": (1, 2),
        "failed_logins": (0, 0),
    },
    "port_scan": {
        "packet_rate": (20, 50),
        "bytes_sent": (200, 800),
        "unique_ports": (20, 100),
        "failed_logins": (0, 0),
    },
    "ddos": {
        "packet_rate": (200, 1000),
        "bytes_sent": (10000, 50000),
        "unique_ports": (1, 3),
        "failed_logins": (0, 0),
    },
    "bruteforce": {
        "packet_rate": (10, 30),
        "bytes_sent": (500, 2000),
        "unique_ports": (1, 2),
        "failed_logins": (10, 100),
    },
    "sql_injection": {
        "packet_rate": (5, 15),
        "bytes_sent": (2000, 8000),
        "unique_ports": (1, 2),
        "failed_logins": (0, 2),
    },
    "malware": {
        "packet_rate": (50, 150),
        "bytes_sent": (5000, 30000),
        "unique_ports": (3, 10),
        "failed_logins": (0, 0),
    }
}
