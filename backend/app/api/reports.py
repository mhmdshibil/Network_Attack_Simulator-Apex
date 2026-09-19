# backend/app/api/reports.py
# This module defines the API route for generating a weekly PDF threat report. It reads the detection
# log, filters it to the last 7 days, and renders a three-page executive PDF (summary, incident
# breakdown, and recommendations) using reportlab. The report is returned as a downloadable file.
#
# reportlab is imported lazily inside the endpoint so that a missing dependency degrades gracefully
# (a 503 response) instead of breaking application startup, mirroring how the LLM features degrade.

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from backend.app.core.paths import DETECTIONS_FILE
from backend.app.core.auth import require_analyst

router = APIRouter(prefix="/api/reports", tags=["reports"])

ORG_NAME = os.getenv("ORG_NAME", "Your Organization")

_ISO_CONTROLS = [
    ("A.12.4.1", "Event logging",                        "detections.csv + real-time audit trail"),
    ("A.12.4.2", "Protection of log information",        "JSONL + DB dual-write fallback"),
    ("A.12.4.3", "Administrator and operator logs",      "decision_audit.csv per response decision"),
    ("A.16.1.1", "Responsibilities and procedures (IDS)","MITRE mapping + automated response engine"),
    ("A.16.1.2", "Reporting security events",            "LLM summaries + PDF threat reports"),
    ("A.16.1.4", "Assessment of security events",        "SHAP explainability + risk scoring 0–100"),
    ("A.16.1.5", "Response to security incidents",       "Triage workflow + SLA deadline tracking"),
    ("A.16.1.6", "Learning from incidents",              "ML evaluation harness + FPR monitoring"),
    ("A.16.1.7", "Collection of evidence",               "Immutable audit trail (CSV + JSONL)"),
]

# detections.csv columns: ip, timestamp, label, action, risk_score
# There is no confidence column, so "confidence" is derived from risk_score
# (the detection engine sets risk_score = min(confidence * 100, 99)).
_REQUIRED_COLS = {"ip", "timestamp", "label", "action", "risk_score"}

# Human-friendly attack labels for the report body.
_LABEL_TITLES = {
    "port_scan": "Port Scan",
    "bruteforce": "Brute Force",
    "ddos": "DDoS",
    "sql_injection": "SQL Injection",
    "malware": "Malware",
    "unknown_anomaly": "Unknown Anomaly",
    "normal": "Normal",
}


def _title(label: str) -> str:
    return _LABEL_TITLES.get(label, str(label).replace("_", " ").title())


def _load_last_7_days():
    """Return (df, start, end). df is None when there is no usable data."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)

    if not DETECTIONS_FILE.exists():
        return None, start, end

    try:
        df = pd.read_csv(DETECTIONS_FILE)
    except Exception:
        return None, start, end

    if df.empty or not _REQUIRED_COLS.issubset(df.columns):
        return None, start, end

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])
    df["risk_score"] = pd.to_numeric(df["risk_score"], errors="coerce").fillna(0.0)

    week = df[df["timestamp"] >= start]
    if week.empty:
        return None, start, end

    return week, start, end


def _recommendations(counts: dict) -> list:
    """Auto-generated recommendation bullets based on detected attack volume."""
    recs = []
    if counts.get("bruteforce", 0) > 10:
        recs.append("Enable account lockout on SSH and admin portals.")
    if counts.get("port_scan", 0) > 20:
        recs.append("Review firewall egress rules.")
    if counts.get("sql_injection", 0) > 5:
        recs.append("Audit web application input validation.")
    if counts.get("ddos", 0) > 3:
        recs.append("Consider rate limiting at the network edge.")
    if counts.get("unknown_anomaly", 0) > 0:
        recs.append("Review zero-day anomaly logs manually.")
    if not recs:
        recs.append("No elevated attack patterns this period. Maintain current monitoring posture.")
    return recs


@router.get("/weekly")
def weekly_report(_: dict = Depends(require_analyst)):
    """
    Generate a weekly PDF threat report and return it as a downloadable file.

    Reads detections.csv, filters to the last 7 days, and renders a 3-page PDF:
    executive summary, incident breakdown, and recommendations. If reportlab is
    not installed, returns 503. If there is no data, returns a valid PDF that
    states "No data available for this period."
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        )
    except ImportError:
        return JSONResponse(
            status_code=503,
            content={"detail": "reportlab not installed — run: pip install reportlab"},
        )

    week, start, end = _load_last_7_days()

    # ── Styles ──────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()
    ink = colors.HexColor("#111111")
    muted = colors.HexColor("#666666")
    line = colors.HexColor("#cccccc")

    h1 = ParagraphStyle("h1", parent=styles["Title"], textColor=ink, fontSize=22, spaceAfter=4, alignment=TA_LEFT)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=ink, fontSize=14, spaceBefore=8, spaceAfter=8)
    body = ParagraphStyle("body", parent=styles["BodyText"], textColor=ink, fontSize=10.5, leading=16)
    sub = ParagraphStyle("sub", parent=styles["BodyText"], textColor=muted, fontSize=10, leading=14)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=12, bulletIndent=2, spaceAfter=6)
    foot = ParagraphStyle("foot", parent=styles["BodyText"], textColor=muted, fontSize=9, alignment=TA_LEFT)

    date_range = f"{start.date().isoformat()} → {end.date().isoformat()}"
    story = []

    # ── Empty-data path ─────────────────────────────────────────────────────
    if week is None:
        story += [
            Paragraph("Apex Argus Security Report", h1),
            Paragraph(date_range, sub),
            Spacer(1, 12 * mm),
            Paragraph("No data available for this period.", h2),
            Spacer(1, 4 * mm),
            Paragraph(
                "No detections were recorded in the last 7 days, or the detection log is empty. "
                "Once the detection pipeline records activity, this report will populate automatically.",
                body,
            ),
            Spacer(1, 8 * mm),
            Paragraph("Generated by Apex Argus SOC Platform", foot),
        ]
        return _render(story, A4, mm, SimpleDocTemplate)

    # ── Aggregates ──────────────────────────────────────────────────────────
    total_incidents = int(len(week))
    blocked = int((week["action"] == "blocked").sum())
    avg_conf = float(week["risk_score"].mean()) / 100.0  # risk_score is 0–100
    label_counts = week["label"].value_counts()
    counts = {k: int(v) for k, v in label_counts.items()}
    most_active = _title(label_counts.index[0]) if len(label_counts) else "—"

    def metric_box(value, label):
        return Table(
            [[Paragraph(f"<b>{value}</b>", ParagraphStyle("mv", parent=body, fontSize=20, textColor=ink))],
             [Paragraph(label, sub)]],
            colWidths=[42 * mm],
            style=TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.75, line),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]),
        )

    # ── PAGE 1 — Executive Summary ──────────────────────────────────────────
    story += [
        Paragraph("Apex Argus Security Report", h1),
        Paragraph(f"Executive Summary &nbsp;·&nbsp; {date_range}", sub),
        Spacer(1, 8 * mm),
    ]
    metrics_row = Table(
        [[metric_box(total_incidents, "Total Incidents"),
          metric_box(blocked, "Blocked Threats"),
          metric_box(f"{avg_conf * 100:.0f}%", "Avg Confidence"),
          metric_box(most_active, "Most Active Type")]],
        colWidths=[45 * mm] * 4,
        style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]),
    )
    story += [metrics_row, Spacer(1, 10 * mm)]

    summary_text = (
        f"During the period {date_range}, the Apex Argus platform recorded "
        f"<b>{total_incidents}</b> security incident(s) across the monitored network. "
        f"Of these, <b>{blocked}</b> were automatically blocked by the response engine, "
        f"with an average detection confidence of <b>{avg_conf * 100:.0f}%</b>. "
        f"The most active attack type this week was <b>{most_active}</b>. "
    )
    if counts:
        breakdown = ", ".join(f"{_title(k)} ({v})" for k, v in list(counts.items())[:5])
        summary_text += f"Observed activity by type: {breakdown}."
    story += [Paragraph("Summary", h2), Paragraph(summary_text, body)]

    # ── PAGE 2 — Incident Breakdown ─────────────────────────────────────────
    story += [PageBreak(), Paragraph("Incident Breakdown", h1), Spacer(1, 6 * mm)]

    header_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, line),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ])

    # By attack type
    type_rows = [["Attack Type", "Count", "Avg Confidence", "Actions Taken"]]
    for label, grp in week.groupby("label"):
        actions = ", ".join(sorted(set(grp["action"].astype(str))))
        type_rows.append([
            _title(label),
            str(len(grp)),
            f"{grp['risk_score'].mean():.0f}%",  # risk_score is 0–100 == confidence %
            actions or "—",
        ])
    story += [Paragraph("By Attack Type", h2),
              Table(type_rows, colWidths=[38 * mm, 20 * mm, 32 * mm, 60 * mm], style=header_style),
              Spacer(1, 8 * mm)]

    # Top 5 attacking IPs
    ip_rows = [["Attacking IP", "Attack Type", "Hit Count", "Status"]]
    top_ips = week["ip"].value_counts().head(5)
    for ip, hits in top_ips.items():
        grp = week[week["ip"] == ip]
        top_label = _title(grp["label"].value_counts().index[0])
        status = str(grp["action"].value_counts().index[0])
        ip_rows.append([str(ip), top_label, str(int(hits)), status])
    story += [Paragraph("Top 5 Attacking IPs", h2),
              Table(ip_rows, colWidths=[45 * mm, 40 * mm, 25 * mm, 40 * mm], style=header_style)]

    # ── PAGE 3 — Recommendations ────────────────────────────────────────────
    story += [PageBreak(), Paragraph("Recommendations", h1), Spacer(1, 6 * mm),
              Paragraph("Prioritised actions based on this week's detected activity:", sub),
              Spacer(1, 4 * mm)]
    for rec in _recommendations(counts):
        story.append(Paragraph(rec, bullet, bulletText="•"))
    story += [Spacer(1, 14 * mm), Paragraph("Generated by Apex Argus SOC Platform", foot)]

    return _render(story, A4, mm, SimpleDocTemplate)


def _load_last_30_days():
    """Return (df, start, end). df is None when there is no usable data."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)
    if not DETECTIONS_FILE.exists():
        return None, start, end
    try:
        df = pd.read_csv(DETECTIONS_FILE)
    except Exception:
        return None, start, end
    if df.empty or not _REQUIRED_COLS.issubset(df.columns):
        return None, start, end
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])
    df["risk_score"] = pd.to_numeric(df["risk_score"], errors="coerce").fillna(0.0)
    month = df[df["timestamp"] >= start]
    return (month if not month.empty else None), start, end


def _load_triage_stats() -> dict:
    """Fetch triage stats from DB. Returns empty dict on any failure."""
    try:
        from backend.app.core import database as _rdb
        from backend.app.core.database import run_async as _run_async
        return _run_async(_rdb.get_triage_stats(), timeout=5)
    except Exception:
        return {}


def _compliance_score(triage: dict) -> tuple:
    """Return (score 0-100, resolution_rate, detection_accuracy, sla_rate)."""
    total = triage.get("total_cases", 0)
    resolved = triage.get("resolved_cases", 0)
    resolution_rate    = resolved / total if total > 0 else 0.0
    detection_accuracy = 1.0 - float(triage.get("false_positive_rate", 0))
    sla_rate           = 1.0 - float(triage.get("sla_breach_rate", 0))
    score = round(resolution_rate * 40 + detection_accuracy * 30 + sla_rate * 30)
    return score, resolution_rate, detection_accuracy, sla_rate


def _compliance_recs(triage: dict) -> list:
    recs = []
    if float(triage.get("sla_breach_rate", 0)) > 0.2:
        recs.append("Assign a dedicated on-call analyst to reduce SLA breach rate.")
    if float(triage.get("false_positive_rate", 0)) > 0.1:
        recs.append("Review ML model thresholds — high false positive rate suggests tuning needed.")
    open_crit = (triage.get("by_severity") or {}).get("critical", 0)
    if open_crit > 0:
        recs.append(f"Immediate action required: {open_crit} critical case(s) unresolved.")
    if not recs:
        recs.append("All compliance metrics are within acceptable thresholds. Maintain current posture.")
    return recs


@router.get("/compliance")
def compliance_report(_: dict = Depends(require_analyst)):
    """
    Generate a 4-page compliance PDF (ISO 27001 mapping, metrics, sign-off block).
    Reads detections.csv for 30-day incident data and the triage table for case metrics.
    Returns 503 if reportlab is not installed.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        )
    except ImportError:
        return JSONResponse(
            status_code=503,
            content={"detail": "reportlab not installed — run: pip install reportlab"},
        )

    month, start, end = _load_last_30_days()
    triage = _load_triage_stats()
    score, res_rate, det_acc, sla_rate = _compliance_score(triage)
    date_range = f"{start.date().isoformat()} → {end.date().isoformat()}"

    # ── Styles ──────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()
    ink   = colors.HexColor("#111111")
    muted = colors.HexColor("#666666")
    line  = colors.HexColor("#cccccc")
    red   = colors.HexColor("#cc2200")
    amber = colors.HexColor("#b86800")
    green = colors.HexColor("#006622")

    h1     = ParagraphStyle("ch1", parent=styles["Title"], textColor=ink, fontSize=22, spaceAfter=4, alignment=TA_LEFT)
    h2     = ParagraphStyle("ch2", parent=styles["Heading2"], textColor=ink, fontSize=14, spaceBefore=8, spaceAfter=8)
    body   = ParagraphStyle("cbody", parent=styles["BodyText"], textColor=ink, fontSize=10.5, leading=16)
    sub    = ParagraphStyle("csub", parent=styles["BodyText"], textColor=muted, fontSize=10, leading=14)
    bullet = ParagraphStyle("cbull", parent=body, leftIndent=12, bulletIndent=2, spaceAfter=6)
    foot   = ParagraphStyle("cfoot", parent=styles["BodyText"], textColor=muted, fontSize=9, alignment=TA_LEFT)
    score_style = ParagraphStyle("cscore", parent=styles["Title"], fontSize=64, textColor=ink, alignment=TA_LEFT, spaceAfter=0)

    header_ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTSIZE",   (0, 0), (-1, -1), 9.5),
        ("GRID",       (0, 0), (-1, -1), 0.5, line),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ])

    # Compliance status label
    if score > 80:
        status_label, status_color = "COMPLIANT", green
    elif score >= 60:
        status_label, status_color = "PARTIAL COMPLIANCE", amber
    else:
        status_label, status_color = "NON-COMPLIANT", red
    status_style = ParagraphStyle("cstatus", parent=styles["Heading1"], textColor=status_color, fontSize=16, spaceAfter=4, alignment=TA_LEFT)

    story = []

    # ── PAGE 1 — Executive Compliance Summary ────────────────────────────────
    story += [
        Paragraph("Security Compliance Report", h1),
        Paragraph(f"{date_range} &nbsp;·&nbsp; Prepared for: {ORG_NAME}", sub),
        Spacer(1, 8 * mm),
        Paragraph(str(score), score_style),
        Paragraph(status_label, status_style),
        Spacer(1, 6 * mm),
    ]

    def pct_row(label, rate, weight):
        bar_w = int(rate * 140)
        return [label, f"{rate * 100:.0f}%", f"×{weight}"]

    comp_rows = [["Component", "Score", "Weight"],
                 pct_row("Case Resolution Rate",  res_rate,  "0.40"),
                 pct_row("Detection Accuracy",    det_acc,   "0.30"),
                 pct_row("SLA Compliance Rate",   sla_rate,  "0.30")]
    story += [
        Paragraph("Compliance Score Breakdown", h2),
        Table(comp_rows, colWidths=[90 * mm, 30 * mm, 30 * mm], style=header_ts),
        Spacer(1, 8 * mm),
        Paragraph(
            f"Compliance score is computed as: (Case Resolution Rate × 0.40) + "
            f"(Detection Accuracy × 0.30) + (SLA Compliance × 0.30). "
            f"A score above 80 indicates full compliance; 60–80 partial compliance; "
            f"below 60 requires immediate remediation action.",
            body,
        ),
    ]

    # ── PAGE 2 — ISO 27001 Control Mapping ──────────────────────────────────
    story += [PageBreak(), Paragraph("ISO 27001 Control Mapping", h1), Spacer(1, 6 * mm)]
    iso_rows = [["Control", "Requirement", "Implementation", "Status"]]
    for ctrl, req, impl in _ISO_CONTROLS:
        iso_rows.append([ctrl, req, impl, "MET"])
    story += [
        Table(
            iso_rows,
            colWidths=[22 * mm, 45 * mm, 80 * mm, 15 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("TEXTCOLOR",  (3, 1), (3, -1), green),
                ("FONTSIZE",   (0, 0), (-1, -1), 8.5),
                ("GRID",       (0, 0), (-1, -1), 0.5, line),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("FONTNAME",   (3, 1), (3, -1), "Helvetica-Bold"),
            ]),
        ),
    ]

    # ── PAGE 3 — Incident Metrics ────────────────────────────────────────────
    story += [PageBreak(), Paragraph("Incident Metrics — Last 30 Days", h1), Spacer(1, 6 * mm)]

    if month is not None:
        def _sev(rs):
            if rs > 85:   return "critical"
            if rs >= 60:  return "high"
            if rs >= 30:  return "medium"
            return "low"
        month = month.copy()
        month["severity"] = month["risk_score"].apply(_sev)
        sev_counts = month["severity"].value_counts()

        met_rows = [["Metric", "Value"]]
        met_rows.append(["Total incidents detected", str(len(month))])
        for sv in ["critical", "high", "medium", "low"]:
            met_rows.append([f"  — {sv.capitalize()}", str(int(sev_counts.get(sv, 0)))])
        met_rows.append(["Mean Time to Detect (MTTD)", "< 1 second (synthetic data — near-instant)"])
        avg_res = triage.get("avg_resolution_minutes")
        met_rows.append(["Mean Time to Respond (MTTR)", f"{avg_res:.0f} min" if avg_res else "N/A (no resolved cases)"])
        breach_rate = triage.get("sla_breach_rate", 0)
        met_rows.append(["SLA compliance rate", f"{(1 - breach_rate) * 100:.0f}%"])
        fp_rate = triage.get("false_positive_rate", 0)
        met_rows.append(["False positive rate", f"{fp_rate * 100:.1f}%"])

        story.append(Table(met_rows, colWidths=[100 * mm, 60 * mm], style=header_ts))
    else:
        story.append(Paragraph("No detection data available for the last 30 days.", body))

    # ── PAGE 4 — Recommendations + Sign-off ─────────────────────────────────
    story += [PageBreak(), Paragraph("Recommendations", h1), Spacer(1, 6 * mm),
              Paragraph("Auto-generated based on current compliance metrics:", sub),
              Spacer(1, 4 * mm)]
    for rec in _compliance_recs(triage):
        story.append(Paragraph(rec, bullet, bulletText="•"))

    story += [
        Spacer(1, 16 * mm),
        Paragraph("Sign-off", h2),
        Spacer(1, 6 * mm),
        Table(
            [["Security Officer:", "_" * 30, "Date:", "_" * 14],
             ["IT Manager:",       "_" * 30, "Date:", "_" * 14]],
            colWidths=[38 * mm, 60 * mm, 18 * mm, 30 * mm],
            style=TableStyle([
                ("FONTSIZE",       (0, 0), (-1, -1), 10),
                ("TOPPADDING",     (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING",  (0, 0), (-1, -1), 8),
                ("LEFTPADDING",    (0, 0), (-1, -1), 0),
            ]),
        ),
        Spacer(1, 14 * mm),
        Paragraph("Generated by Apex Argus SOC Platform v2.0", foot),
    ]

    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title="Apex Argus Compliance Report",
    )
    doc.build(story)
    filename = f"apex_compliance_{datetime.now(timezone.utc).date().isoformat()}.pdf"
    return FileResponse(path, media_type="application/pdf", filename=filename,
                        background=BackgroundTask(os.unlink, path))


def _render(story, pagesize, mm, SimpleDocTemplate) -> FileResponse:
    """Render a platypus story to a temp PDF and return it as a download."""
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    doc = SimpleDocTemplate(
        path, pagesize=pagesize,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title="Apex Argus Security Report",
    )
    doc.build(story)
    filename = f"apex_report_{datetime.now(timezone.utc).date().isoformat()}.pdf"
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
        background=BackgroundTask(os.unlink, path),  # delete temp file after send
    )
