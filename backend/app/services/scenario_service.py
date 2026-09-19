"""
Scenario service — Phase 4A (Demo Polish).

Runs the "Corporate Breach Attempt" scripted attack scenario, firing
pre-defined detections in sequence and broadcasting narrative context
via WebSocket. Bypasses the ML model for deterministic demo results.
"""
import asyncio
import csv
from datetime import datetime, timezone
from typing import Optional

from backend.app.core.paths import DETECTIONS_FILE
from backend.app.services.ws_manager import manager as ws_manager

try:
    from backend.app.core import database as _db
except Exception:
    _db = None

try:
    from backend.app.ml.mitre_mapping import get_mitre
except Exception:
    def get_mitre(_): return None  # type: ignore[misc]


# ── Scenario definitions ──────────────────────────────────────────────────────

SCENARIOS: dict = {
    "corporate_breach": {
        "name": "Corporate Breach Attempt",
        "description": "Multi-vector attack: recon → credential attack → SQLi → malware → DDoS",
        "duration_seconds": 180,
        "acts": [
            {
                "act": 1,
                "name": "Reconnaissance",
                "text": "Attacker begins reconnaissance — scanning for open ports on server infrastructure",
                "attacks": [
                    {"label": "port_scan",  "ip": "185.220.101.5", "confidence": 0.95, "risk": 95, "zone": "server_infrastructure"},
                    {"label": "port_scan",  "ip": "185.220.101.5", "confidence": 0.95, "risk": 95, "zone": "server_infrastructure"},
                    {"label": "port_scan",  "ip": "185.220.101.5", "confidence": 0.95, "risk": 95, "zone": "server_infrastructure"},
                ],
                "delay_between": 8,
                "inter_act_delay": 14,
                "progress_start": 0,
                "progress_end": 20,
            },
            {
                "act": 2,
                "name": "Credential Attack",
                "text": "Escalating to credential stuffing — targeting management systems",
                "attacks": [
                    {"label": "bruteforce", "ip": "185.220.101.5", "confidence": 0.98, "risk": 98, "zone": "management_office"},
                    {"label": "bruteforce", "ip": "185.220.101.5", "confidence": 0.98, "risk": 98, "zone": "management_office"},
                ],
                "delay_between": 8,
                "inter_act_delay": 22,
                "progress_start": 20,
                "progress_end": 40,
            },
            {
                "act": 3,
                "name": "Exploitation Attempt",
                "text": "SQL injection attempt detected on application server",
                "attacks": [
                    {"label": "sql_injection", "ip": "185.220.101.5", "confidence": 0.87, "risk": 87, "zone": "server_infrastructure"},
                ],
                "delay_between": 0,
                "inter_act_delay": 30,
                "progress_start": 40,
                "progress_end": 60,
            },
            {
                "act": 4,
                "name": "Lateral Movement",
                "text": "Malware deployment detected — possible lateral movement to endpoint network",
                "attacks": [
                    {"label": "malware", "ip": "185.220.101.6", "confidence": 0.99, "risk": 99, "zone": "endpoint_network"},
                ],
                "delay_between": 0,
                "inter_act_delay": 44,
                "progress_start": 60,
                "progress_end": 80,
            },
            {
                "act": 5,
                "name": "DDoS Distraction",
                "text": "DDoS attack launched as distraction — classic multi-vector campaign",
                "attacks": [
                    {"label": "ddos", "ip": "45.142.212.100", "confidence": 0.99, "risk": 99, "zone": "server_infrastructure"},
                    {"label": "ddos", "ip": "45.142.212.100", "confidence": 0.99, "risk": 99, "zone": "server_infrastructure"},
                ],
                "delay_between": 8,
                "inter_act_delay": 0,
                "progress_start": 80,
                "progress_end": 100,
            },
        ],
    }
}

# ── Module-level runtime state ────────────────────────────────────────────────
_is_running: bool = False
_stop_flag: bool = False
_current_act: int = 0
_current_act_name: str = ""
_progress: int = 0
_narrative_text: str = ""
_completed_acts: int = 0
_scenario_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _action_for_risk(risk: float) -> str:
    if risk >= 85:
        return "blocked"
    if risk >= 60:
        return "rate_limited"
    return "monitored"


def _write_detection(*, source_ip: str, label: str, confidence: float, risk: float, zone: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    action = _action_for_risk(risk)
    mitre = get_mitre(label)

    row = {"ip": source_ip, "timestamp": ts, "label": label, "action": action, "risk_score": risk}

    if DETECTIONS_FILE.exists():
        with open(DETECTIONS_FILE, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=list(row.keys())).writerow(row)
    else:
        DETECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DETECTIONS_FILE, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()))
            w.writeheader()
            w.writerow(row)

    if _db is not None:
        _db.save_detection_safe(
            ip=source_ip, timestamp=ts, label=label, action=action,
            risk_score=risk, confidence=confidence, target_zone=zone,
            packets_per_second=0.0, avg_request_rate=0.0,
            failed_connections=None, unique_ports=None,
            mitre_tactic=(mitre or {}).get("tactic"),
            mitre_technique=(mitre or {}).get("technique_id"),
            sensor_mode="scenario",
        )
        try:
            _db.create_triage_case_safe(
                detection_id=f"{source_ip}:{ts}",
                ip=source_ip, label=label, risk_score=risk,
            )
        except Exception:
            pass

    detection_dict = {
        "ip": source_ip, "timestamp": ts, "label": label, "action": action,
        "risk_score": risk, "confidence": round(confidence, 3),
        "target_zone": zone,
    }

    ws_manager.broadcast_sync({"type": "detection", **detection_dict, "mitre": mitre})

    try:
        from backend.app.services.notification_service import service as _notify
        _notify.maybe_notify(detection_dict)
    except Exception:
        pass

    print(f"[SCENARIO] {action.upper()} — {label} from {source_ip} (risk={risk}, zone={zone})")


async def _run_scenario_loop(name: str) -> None:
    global _is_running, _stop_flag, _current_act, _current_act_name
    global _progress, _narrative_text, _completed_acts

    scenario = SCENARIOS[name]
    acts = scenario["acts"]

    _is_running = True
    _stop_flag = False
    _completed_acts = 0

    try:
        for act_def in acts:
            if _stop_flag:
                break

            _current_act = act_def["act"]
            _current_act_name = act_def["name"]
            _narrative_text = act_def["text"]
            _progress = act_def["progress_start"]

            ws_manager.broadcast_sync({
                "type": "scenario_narrative",
                "act": act_def["act"],
                "act_name": act_def["name"],
                "text": act_def["text"],
                "progress": _progress,
            })

            n_attacks = len(act_def["attacks"])
            for j, attack in enumerate(act_def["attacks"]):
                if _stop_flag:
                    break

                await asyncio.to_thread(
                    _write_detection,
                    source_ip=attack["ip"],
                    label=attack["label"],
                    confidence=attack["confidence"],
                    risk=attack["risk"],
                    zone=attack["zone"],
                )

                _progress = act_def["progress_start"] + round(
                    (act_def["progress_end"] - act_def["progress_start"]) * (j + 1) / n_attacks
                )

                ws_manager.broadcast_sync({
                    "type": "scenario_narrative",
                    "act": act_def["act"],
                    "act_name": act_def["name"],
                    "text": act_def["text"],
                    "progress": _progress,
                })

                if j < n_attacks - 1 and act_def["delay_between"] > 0:
                    for _ in range(act_def["delay_between"]):
                        if _stop_flag:
                            break
                        await asyncio.sleep(1)

            _completed_acts += 1
            _progress = act_def["progress_end"]

            delay = act_def.get("inter_act_delay", 0)
            for _ in range(delay):
                if _stop_flag:
                    break
                await asyncio.sleep(1)

    finally:
        final_text = "Scenario complete." if _progress >= 100 else "Scenario stopped."
        ws_manager.broadcast_sync({
            "type": "scenario_narrative",
            "act": _current_act,
            "act_name": _current_act_name,
            "text": final_text,
            "progress": _progress,
            "complete": True,
        })
        _is_running = False
        _stop_flag = False


# ── Public service class ──────────────────────────────────────────────────────

class ScenarioService:

    async def run_scenario(self, name: str) -> None:
        global _scenario_task
        if _is_running:
            raise RuntimeError("Scenario already running")
        _scenario_task = asyncio.create_task(_run_scenario_loop(name))

    def stop_scenario(self) -> int:
        global _stop_flag
        _stop_flag = True
        return _completed_acts

    def get_status(self) -> dict:
        return {
            "is_running": _is_running,
            "current_act": _current_act,
            "act_name": _current_act_name,
            "progress": _progress,
            "narrative_text": _narrative_text,
        }


service = ScenarioService()
