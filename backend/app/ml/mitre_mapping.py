"""
MITRE ATT&CK technique reference table — Phase 9.

Mapping from internal attack labels to the closest ATT&CK technique.
Applied at API response time; no change to the stored CSV schema.
"""

MITRE = {
    "port_scan": {
        "technique_id": "T1046",
        "technique":    "Network Service Discovery",
        "tactic":       "Discovery",
        "tactic_id":    "TA0007",
        "url":          "https://attack.mitre.org/techniques/T1046/",
    },
    "bruteforce": {
        "technique_id": "T1110",
        "technique":    "Brute Force",
        "tactic":       "Credential Access",
        "tactic_id":    "TA0006",
        "url":          "https://attack.mitre.org/techniques/T1110/",
    },
    "ddos": {
        "technique_id": "T1498",
        "technique":    "Network Denial of Service",
        "tactic":       "Impact",
        "tactic_id":    "TA0040",
        "url":          "https://attack.mitre.org/techniques/T1498/",
    },
    "sql_injection": {
        "technique_id": "T1190",
        "technique":    "Exploit Public-Facing Application",
        "tactic":       "Initial Access",
        "tactic_id":    "TA0001",
        "url":          "https://attack.mitre.org/techniques/T1190/",
    },
    "malware": {
        "technique_id": "T1587",
        "technique":    "Develop Capabilities",
        "tactic":       "Resource Development",
        "tactic_id":    "TA0042",
        "url":          "https://attack.mitre.org/techniques/T1587/",
    },
    "unknown_anomaly": {
        "technique_id": "T1036",
        "technique":    "Masquerading",
        "tactic":       "Defense Evasion",
        "tactic_id":    "TA0005",
        "url":          "https://attack.mitre.org/techniques/T1036/",
    },
}

_FALLBACK = {
    "technique_id": "T0000",
    "technique":    "Unknown",
    "tactic":       "Unknown",
    "tactic_id":    "TA0000",
    "url":          "https://attack.mitre.org/",
}


def get_mitre(label: str) -> dict:
    """Return MITRE ATT&CK mapping for a given attack label."""
    return MITRE.get(label, _FALLBACK)


def enrich(detection: dict) -> dict:
    """Return detection dict with a 'mitre' key added."""
    return {**detection, "mitre": get_mitre(detection.get("label", ""))}
