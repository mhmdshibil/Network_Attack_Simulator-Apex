#!/usr/bin/env python3
"""
sensor_agent.py — bridge between the Apex Argus simulation and a real network.

This is a standalone process (not part of the FastAPI app). It builds 5-second
feature windows — one record per source IP with the four features the ML model
expects — and POSTs them to the backend:

    packets_per_second (float)   avg_request_rate (float)
    failed_connections (int)     unique_ports (int)

Two modes, selected by SENSOR_MODE:

  demo (default)  — reuse the synthetic generators in scripts/, aggregate a
                    window, and POST it. No special privileges required.
  real            — capture live packets with pyshark on SENSOR_INTERFACE and
                    derive the same features. Needs root / CAP_NET_RAW and the
                    optional `pyshark` dependency.

Config (env vars, with defaults):
  SENSOR_MODE=demo|real         (default: demo)
  SENSOR_INTERFACE=eth0         (default: eth0, real mode only)
  BACKEND_URL=http://localhost:8000
  SENSOR_INTERVAL=5             (window length in seconds)

Run:
  python sensor_agent.py                 # demo mode
  SENSOR_MODE=real sudo -E python sensor_agent.py

Ctrl+C shuts down gracefully. If the backend is unreachable the agent logs the
error, waits one interval, and retries — it never crashes.
"""
import os
import re
import sys
import time
import signal
from collections import defaultdict
from datetime import datetime, timezone

import requests

# ── Config ──────────────────────────────────────────────────────────────────
SENSOR_MODE      = os.getenv("SENSOR_MODE", "demo").lower()
SENSOR_INTERFACE = os.getenv("SENSOR_INTERFACE", "eth0")
BACKEND_URL      = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
SENSOR_INTERVAL  = int(os.getenv("SENSOR_INTERVAL", "5"))

# Ingest endpoint: POST /api/detections accepts one aggregated feature window per
# source IP (schema: FeatureWindowIn). The agent posts one record per unique IP.
INGEST_ENDPOINT = f"{BACKEND_URL}/api/detections"

# ── Graceful shutdown ───────────────────────────────────────────────────────
_running = True


def _handle_stop(signum, frame):
    global _running
    _running = False
    print("\n[SENSOR] Shutdown requested — finishing current window and exiting…", flush=True)


def _interruptible_sleep(seconds: float) -> None:
    """Sleep that returns early when a shutdown signal arrives."""
    end = time.monotonic() + seconds
    while _running and time.monotonic() < end:
        time.sleep(0.1)


# ── Networking ──────────────────────────────────────────────────────────────
def post_events(events: list, mode: str) -> list:
    """
    POST each feature record to the backend as an individual window
    (matches the /api/detections FeatureWindowIn schema). Never raises — on a
    connection error it logs and returns so the caller retries next window.

    Returns a list of per-IP result dicts: {ip, status, label, action}.
    """
    window_start = datetime.now(timezone.utc).isoformat()
    accepted = 0
    results = []
    for ev in events:
        record = {
            "source_ip": ev["source_ip"],
            "packets_per_second": ev["packets_per_second"],
            "avg_request_rate": ev["avg_request_rate"],
            "failed_connections": ev["failed_connections"],
            "unique_ports": ev["unique_ports"],
            "bytes_per_packet": ev.get("bytes_per_packet", 300.0),
            "connection_duration": ev.get("connection_duration", 2.0),
            "payload_entropy": ev.get("payload_entropy", 4.0),
            "window_start": window_start,
            "sensor_mode": mode,
        }
        if ev.get("target_zone"):
            record["target_zone"] = ev["target_zone"]
        try:
            resp = requests.post(INGEST_ENDPOINT, json=record, timeout=10)
            if resp.status_code == 200:
                accepted += 1
                body = resp.json()
                results.append({"ip": ev["source_ip"], "status": 200,
                                "label": body.get("label"), "action": body.get("action")})
            else:
                print(f"[SENSOR] {record['source_ip']} → HTTP {resp.status_code}", flush=True)
                results.append({"ip": ev["source_ip"], "status": resp.status_code,
                                "label": None, "action": None})
        except requests.RequestException as exc:
            print(f"[SENSOR] Backend unreachable ({exc}). Will retry next window.", flush=True)
            return results
    print(f"[SENSOR] {accepted}/{len(events)} records accepted (HTTP 200)", flush=True)
    return results


# ── Demo mode ───────────────────────────────────────────────────────────────
def _demo_raw_rows() -> list:
    """
    Produce a batch of synthetic rows using the existing generators.
    Each row matches the generator schema:
      [timestamp, source_ip, destination_ip, destination_port,
       protocol, packet_count, request_rate, success_flag, label]
    """
    import random
    from scripts.generate_normal_traffic import generate_normal_traffic
    from scripts.generate_port_scan_attack import generate_port_scan
    from scripts.generate_ddos_attack import generate_ddos
    from scripts.generate_bruteforce_attack import generate_bruteforce
    from scripts.generate_sql_injection_attack import generate_sql_injection
    from scripts.generate_malware_traffic import generate_malware_traffic

    attack_generators = [
        lambda: generate_port_scan(n_ports=40),
        lambda: generate_ddos(n_packets=30),
        lambda: generate_bruteforce(n_attempts=25),
        lambda: generate_sql_injection(n_requests=15),
        lambda: generate_malware_traffic(n_packets=20),
    ]

    rows = list(generate_normal_traffic(n=60))
    rows += random.choice(attack_generators)()
    return rows


# Column positions in the generator row schema (v2 — 12 columns)
_COL_SRC_IP       = 1
_COL_DST_PORT     = 3
_COL_PKT_CNT      = 5
_COL_REQ_RATE     = 6
_COL_SUCCESS      = 7
_COL_LABEL        = 8
_COL_BYTES_PER_PKT = 9
_COL_CONN_DUR     = 10
_COL_ENTROPY      = 11


def _aggregate_rows(rows: list) -> list:
    """Collapse raw rows into one feature record per source IP."""
    by_ip = defaultdict(lambda: {
        "packets": 0, "rates": [], "failed": 0, "ports": set(), "labels": defaultdict(int),
        "bpp": [], "dur": [], "ent": [],
    })
    for r in rows:
        src = r[_COL_SRC_IP]
        acc = by_ip[src]
        acc["packets"] += int(r[_COL_PKT_CNT])
        acc["rates"].append(float(r[_COL_REQ_RATE]))
        if not bool(r[_COL_SUCCESS]):
            acc["failed"] += 1
        acc["ports"].add(r[_COL_DST_PORT])
        acc["labels"][r[_COL_LABEL]] += 1
        # v2 features — guard for old 9-column rows that may still appear
        if len(r) > _COL_ENTROPY:
            try:
                acc["bpp"].append(float(r[_COL_BYTES_PER_PKT]))
                acc["dur"].append(float(r[_COL_CONN_DUR]))
                acc["ent"].append(float(r[_COL_ENTROPY]))
            except (TypeError, ValueError):
                pass

    events = []
    for src, acc in by_ip.items():
        rates = acc["rates"] or [0.0]
        events.append({
            "source_ip": src,
            "packets_per_second": round(acc["packets"] / SENSOR_INTERVAL, 3),
            "avg_request_rate": round(sum(rates) / len(rates), 3),
            "failed_connections": int(acc["failed"]),
            "unique_ports": int(len(acc["ports"])),
            "bytes_per_packet": round(sum(acc["bpp"]) / len(acc["bpp"]), 3) if acc["bpp"] else 300.0,
            "connection_duration": round(sum(acc["dur"]) / len(acc["dur"]), 3) if acc["dur"] else 2.0,
            "payload_entropy": round(sum(acc["ent"]) / len(acc["ent"]), 3) if acc["ent"] else 4.0,
            # observed label is demo-only metadata; real mode omits it
            "observed_label": max(acc["labels"], key=acc["labels"].get),
        })
    return events


def run_demo() -> None:
    print(f"[SENSOR] Starting in DEMO mode → {INGEST_ENDPOINT} every {SENSOR_INTERVAL}s", flush=True)
    while _running:
        rows = _demo_raw_rows()
        events = _aggregate_rows(rows)
        print(f"[DEMO] Sending synthetic window: {len(rows)} events, {len(events)} unique IPs", flush=True)
        post_events(events, mode="demo")
        _interruptible_sleep(SENSOR_INTERVAL)


# ── Real mode ───────────────────────────────────────────────────────────────
MIN_PACKETS = 3            # noise filter — ignore source IPs with < 3 packets
TEST_CAPTURE_SECONDS = 10  # duration for --test-capture

# Network subnets → NetworkMap zone ids (matches org_profile.py / NetworkMap.jsx)
_ZONE_BY_OCTET = {1: "admin", 2: "student_wifi", 3: "server_room", 4: "lab"}


def _dst_zone(ip_dst) -> "str | None":
    """Map a destination IP to a network zone id, else None."""
    m = re.match(r"^10\.0\.(\d{1,3})\.", ip_dst or "")
    return _ZONE_BY_OCTET.get(int(m.group(1))) if m else None


def _tcp_flag(tcp, field: str, bit: int) -> bool:
    """
    Read a TCP flag robustly. pyshark exposes flags either as boolean-ish
    fields (tcp.flags_syn == '1') or as a packed hex value (tcp.flags).
    """
    v = getattr(tcp, field, None)
    if v is not None:
        return str(v) in ("1", "True", "true")
    try:
        return bool(int(getattr(tcp, "flags", "0x0"), 16) & bit)
    except Exception:
        return False


def _ensure_pyshark():
    try:
        import pyshark  # noqa: F401
        return pyshark
    except ImportError:
        print("[SENSOR] pyshark is not installed. Install it for real mode:", flush=True)
        print("           pip install pyshark   (also requires tshark/Wireshark)", flush=True)
        sys.exit(1)


def _explain_capture_error(exc: Exception) -> None:
    """Print a clear, actionable message for common capture failures, then exit."""
    msg = str(exc).lower()
    print(f"[REAL] Packet capture failed on interface '{SENSOR_INTERFACE}'.", flush=True)
    if any(k in msg for k in ("permission", "denied", "root", "cap_net_raw", "not permitted")):
        print("  → Permission denied. Run as root, or grant capture capability:", flush=True)
        print("      sudo -E python sensor_agent.py        (simplest)", flush=True)
        print("      sudo setcap cap_net_raw+ep $(which dumpcap)", flush=True)
    elif any(k in msg for k in ("no such", "not found", "unknown", "no interface", "couldn't run")):
        print(f"  → Interface '{SENSOR_INTERFACE}' not found. List interfaces with:  tshark -D", flush=True)
        print("    Then set SENSOR_INTERFACE to a valid name.", flush=True)
    elif "tshark" in msg or "wireshark" in msg:
        print("  → tshark not found. Install Wireshark/tshark and ensure it is on PATH.", flush=True)
    else:
        print(f"  → {exc}", flush=True)
    sys.exit(1)


def _capture_window(duration: int):
    """
    Sniff for `duration` seconds and derive per-source-IP features.

    Returns (events, packet_count, source_ip_count) where events is the list of
    feature records for source IPs that sent >= MIN_PACKETS packets.
    """
    pyshark = _ensure_pyshark()

    stats = defaultdict(lambda: {
        "packets": 0, "syn": 0, "failed": 0, "ports": set(), "zones": defaultdict(int),
        "total_bytes": 0,
    })
    packet_count = 0

    capture = pyshark.LiveCapture(interface=SENSOR_INTERFACE)
    try:
        capture.sniff(timeout=duration)
        captured = list(capture)
    finally:
        try:
            capture.close()
        except Exception:
            pass

    for pkt in captured:
        try:
            # FILTER: only packets with an IP layer (skip ARP, STP, etc.)
            if not hasattr(pkt, "ip"):
                continue
            src = pkt.ip.src
            acc = stats[src]
            acc["packets"] += 1
            packet_count += 1
            try:
                acc["total_bytes"] += int(pkt.length)
            except Exception:
                pass

            # target_zone from destination IP
            zone = _dst_zone(getattr(pkt.ip, "dst", None))
            if zone:
                acc["zones"][zone] += 1

            # TCP: SYN (new connections), RST (failed), dst port
            if hasattr(pkt, "tcp"):
                if _tcp_flag(pkt.tcp, "flags_syn", 0x02):
                    acc["syn"] += 1
                if _tcp_flag(pkt.tcp, "flags_reset", 0x04):
                    acc["failed"] += 1
                dport = getattr(pkt.tcp, "dstport", None)
                if dport is not None:
                    acc["ports"].add(str(dport))
            # UDP: dst port
            elif hasattr(pkt, "udp"):
                dport = getattr(pkt.udp, "dstport", None)
                if dport is not None:
                    acc["ports"].add(str(dport))
            # ICMP type 3 = destination unreachable → failed connection
            elif hasattr(pkt, "icmp"):
                if str(getattr(pkt.icmp, "type", "")) == "3":
                    acc["failed"] += 1
        except Exception:
            continue  # never crash on a malformed packet — skip and continue

    events = []
    for src, acc in stats.items():
        if acc["packets"] < MIN_PACKETS:
            continue  # noise filter
        zone = max(acc["zones"], key=acc["zones"].get) if acc["zones"] else None
        bpp = round(acc["total_bytes"] / acc["packets"], 2) if acc["packets"] > 0 else 300.0
        events.append({
            "source_ip": src,
            "packets_per_second": round(acc["packets"] / duration, 3),
            "avg_request_rate": round(acc["syn"] / duration, 3),
            "failed_connections": int(acc["failed"]),
            "unique_ports": int(len(acc["ports"])),
            "bytes_per_packet": bpp,
            "connection_duration": 0.0,   # not derivable without session tracking
            "payload_entropy": 0.0,       # not derivable without payload access
            "target_zone": zone,
        })
    return events, packet_count, len(stats)


def run_real() -> None:
    _ensure_pyshark()
    print(f"[SENSOR] Starting in REAL mode on {SENSOR_INTERFACE} → {INGEST_ENDPOINT}", flush=True)
    while _running:
        try:
            events, packet_count, source_ips = _capture_window(SENSOR_INTERVAL)
        except Exception as exc:
            # A capture failure on a live interface is not transient (bad
            # interface / no permission) — explain clearly and exit.
            _explain_capture_error(exc)
            return

        print(
            f"[REAL] Window complete — {packet_count} packets, {source_ips} source IPs, "
            f"posting {len(events)} windows (≥{MIN_PACKETS} packets)",
            flush=True,
        )
        results = post_events(events, mode="real")
        for r in results:
            if r["status"] == 200:
                print(f"[REAL] Posted {r['ip']}: label={r['label']} action={r['action']}", flush=True)


def run_test_capture() -> None:
    """Capture for TEST_CAPTURE_SECONDS and print a summary table. Never posts."""
    _ensure_pyshark()
    print(f"[TEST] Capturing {TEST_CAPTURE_SECONDS}s on '{SENSOR_INTERFACE}' (no posting)…", flush=True)
    try:
        events, packet_count, source_ips = _capture_window(TEST_CAPTURE_SECONDS)
    except Exception as exc:
        _explain_capture_error(exc)
        return

    print(f"[TEST] Saw {packet_count} packets from {source_ips} source IPs; "
          f"{len(events)} with ≥{MIN_PACKETS} packets\n", flush=True)
    if not events:
        print("[TEST] No qualifying source IPs. Is there traffic on this interface?", flush=True)
        return

    header = f"{'SOURCE IP':<18} {'PKT/S':>8} {'SYN/S':>8} {'FAILED':>7} {'PORTS':>6}  ZONE"
    print(header)
    print("-" * len(header))
    for ev in sorted(events, key=lambda e: -e["packets_per_second"]):
        print(f"{ev['source_ip']:<18} {ev['packets_per_second']:>8.2f} "
              f"{ev['avg_request_rate']:>8.2f} {ev['failed_connections']:>7} "
              f"{ev['unique_ports']:>6}  {ev['target_zone'] or '-'}")


# ── Entry point ─────────────────────────────────────────────────────────────
def main() -> None:
    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    # --test-capture: verify the sensor sees traffic before going live (no posting)
    if "--test-capture" in sys.argv:
        run_test_capture()
        return

    if SENSOR_MODE == "real":
        run_real()
    else:
        run_demo()

    print("[SENSOR] Stopped cleanly.", flush=True)


if __name__ == "__main__":
    main()
