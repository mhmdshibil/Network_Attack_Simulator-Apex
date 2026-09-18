"""
NotificationService — Phase 3 / Task 3.

Fires Slack and email alerts when a detection crosses a severity threshold.

Trigger conditions (any one is sufficient):
  • attack_type == "malware"  and confidence > 0.8
  • risk_score >= 90
  • attack_type == "ddos"     and confidence > 0.9
  • action == "blocked"  (newly blocked IP)
  • 3+ detections from the same IP within 60 seconds (burst)

Deduplication: the same IP is not re-notified within 5 minutes.
Rate limiting:  max 10 Slack messages/minute, max 20 emails/hour.

Both channels are configured via env vars; if not set they are skipped silently.
Notifications are sent in background daemon threads so they never block detections.
httpx is used for Slack (already in requirements). Email uses built-in smtplib.
"""
import os
import smtplib
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Config from env
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "").strip()
SMTP_HOST         = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT         = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER         = os.getenv("SMTP_USER", "").strip()
SMTP_PASS         = os.getenv("SMTP_PASS", "").strip()
ALERT_EMAIL_TO    = os.getenv("ALERT_EMAIL_TO", "").strip()

_DEDUP_SECONDS   = 300   # 5 minutes per IP
_BURST_WINDOW    = 60    # seconds for burst detection
_BURST_THRESHOLD = 3     # min detections within window
_SLACK_MAX_MIN   = 10    # max Slack messages per minute
_EMAIL_MAX_HOUR  = 20    # max emails per hour


class NotificationService:
    def __init__(self):
        # ip → monotonic timestamp of last notification
        self._dedup: dict[str, float] = {}
        # ip → list of monotonic timestamps of recent detections (burst tracking)
        self._burst: dict = defaultdict(list)
        # sliding-window rate limit trackers (monotonic timestamps)
        self._slack_times: list = []
        self._email_times: list = []
        # in-memory notification log (last 50 entries)
        self._log: list = []
        self._log_lock = threading.Lock()

    # ── Configuration ────────────────────────────────────────────────────────

    @property
    def slack_configured(self) -> bool:
        return bool(SLACK_WEBHOOK_URL)

    @property
    def email_configured(self) -> bool:
        return bool(SMTP_HOST and SMTP_USER and SMTP_PASS and ALERT_EMAIL_TO)

    # ── Public entry point (called from detection pipeline) ──────────────────

    def maybe_notify(self, detection: dict) -> None:
        """Check triggers, apply dedup, and fire notifications in the background."""
        try:
            should, reason = self._check_triggers(detection)
            if not should:
                return
            ip  = detection.get("ip", "")
            now = time.monotonic()
            # Dedup: skip if notified same IP recently
            if now - self._dedup.get(ip, 0) < _DEDUP_SECONDS:
                return
            self._dedup[ip] = now
            # Fire in daemon thread so detection pipeline is never blocked
            threading.Thread(
                target=self._notify_all,
                args=(detection, reason),
                daemon=True,
            ).start()
        except Exception:
            pass

    # ── Trigger logic ────────────────────────────────────────────────────────

    def _check_triggers(self, detection: dict) -> tuple:
        """Return (should_notify: bool, reason: str)."""
        ip    = detection.get("ip", "")
        label = detection.get("label", "")
        conf  = float(detection.get("confidence") or 0)
        risk  = float(detection.get("risk_score") or 0)
        action = detection.get("action", "")

        now = time.monotonic()

        # Track burst
        ip_times = self._burst[ip]
        ip_times.append(now)
        # Prune old entries
        self._burst[ip] = [t for t in ip_times if now - t <= _BURST_WINDOW]
        burst_count = len(self._burst[ip])

        if label == "malware" and conf > 0.8:
            return True, "malware_high_confidence"
        if risk >= 90:
            return True, "risk_score_critical"
        if label == "ddos" and conf > 0.9:
            return True, "ddos_high_confidence"
        if action == "blocked":
            return True, "newly_blocked"
        if burst_count >= _BURST_THRESHOLD:
            return True, f"burst_{burst_count}_in_{_BURST_WINDOW}s"
        return False, ""

    # ── Dispatch ─────────────────────────────────────────────────────────────

    def _notify_all(self, detection: dict, reason: str) -> None:
        """Called in a background thread. Sends to all configured channels."""
        slack_status = self._send_slack(detection, reason)
        email_status = self._send_email(detection, reason)
        self._append_log(detection, reason, slack_status, email_status)

    def _can_slack(self) -> bool:
        now = time.monotonic()
        self._slack_times = [t for t in self._slack_times if now - t <= 60]
        return len(self._slack_times) < _SLACK_MAX_MIN

    def _can_email(self) -> bool:
        now = time.monotonic()
        self._email_times = [t for t in self._email_times if now - t <= 3600]
        return len(self._email_times) < _EMAIL_MAX_HOUR

    # ── Slack ────────────────────────────────────────────────────────────────

    def _send_slack(self, detection: dict, reason: str) -> str:
        if not self.slack_configured:
            print("[NOTIFY] Slack not configured")
            return "not_configured"
        if not self._can_slack():
            print(f"[NOTIFY] Slack rate limit reached ({_SLACK_MAX_MIN}/min)")
            return "skipped"
        try:
            import httpx
        except ImportError:
            return "failed"
        label  = detection.get("label", "unknown")
        ip     = detection.get("ip", "—")
        conf   = detection.get("confidence")
        action = detection.get("action", "—")
        risk   = detection.get("risk_score")
        mitre  = (detection.get("mitre") or {}).get("technique_id", "")
        sev    = _severity_from_risk(risk)
        icon   = "🚨" if sev in ("critical", "high") else "⚠️"
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"{icon} Apex-Kinetics Alert — {label.replace('_', ' ').title()}"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Attack Type:*\n{label.replace('_', ' ')}"},
                {"type": "mrkdwn", "text": f"*Source IP:*\n{ip}"},
                {"type": "mrkdwn", "text": f"*Confidence:*\n{f'{conf*100:.0f}%' if conf is not None else '—'}"},
                {"type": "mrkdwn", "text": f"*Action Taken:*\n{action.upper()}"},
                {"type": "mrkdwn", "text": f"*Risk Score:*\n{risk:.0f}" if risk is not None else "*Risk Score:*\n—"},
                {"type": "mrkdwn", "text": f"*MITRE:*\n{mitre}" if mitre else "*Trigger:*\n" + reason},
            ]},
            {"type": "section", "text": {"type": "mrkdwn", "text": "View in Dashboard → http://localhost:3000"}},
        ]
        try:
            r = httpx.post(SLACK_WEBHOOK_URL, json={"blocks": blocks}, timeout=5)
            self._slack_times.append(time.monotonic())
            return "sent" if r.status_code == 200 else "failed"
        except Exception as e:
            print(f"[NOTIFY] Slack send failed: {e}")
            return "failed"

    # ── Email ────────────────────────────────────────────────────────────────

    def _send_email(self, detection: dict, reason: str) -> str:
        if not self.email_configured:
            return "not_configured"
        if not self._can_email():
            print(f"[NOTIFY] Email rate limit reached ({_EMAIL_MAX_HOUR}/hr)")
            return "skipped"
        try:
            threading.Thread(
                target=self._send_email_blocking,
                args=(detection, reason),
                daemon=True,
            ).start()
            self._email_times.append(time.monotonic())
            return "sent"
        except Exception:
            return "failed"

    def _send_email_blocking(self, detection: dict, reason: str) -> None:
        label  = detection.get("label", "unknown")
        ip     = detection.get("ip", "—")
        conf   = detection.get("confidence")
        action = detection.get("action", "—")
        risk   = detection.get("risk_score")
        mitre  = detection.get("mitre") or {}
        shap   = detection.get("shap_top3") or []
        sev    = _severity_from_risk(risk)

        subject = f"[APEX] {sev.upper()} Alert — {label.replace('_', ' ')} from {ip}"

        lines = [
            "Apex-Kinetics Security Alert",
            "=" * 40,
            f"Attack Type : {label.replace('_', ' ')}",
            f"Source IP   : {ip}",
            f"Confidence  : {f'{conf*100:.0f}%' if conf is not None else '—'}",
            f"Risk Score  : {risk:.0f}" if risk is not None else "Risk Score  : —",
            f"Action Taken: {action.upper()}",
            f"Severity    : {sev.upper()}",
            f"Trigger     : {reason}",
        ]
        if mitre.get("technique_id") and mitre["technique_id"] != "T0000":
            lines += [
                "",
                "MITRE ATT&CK",
                f"  Technique : {mitre.get('technique_id')} — {mitre.get('technique', '—')}",
                f"  Tactic    : {mitre.get('tactic', '—')}",
            ]
        if shap:
            lines += ["", "Top Feature Contributions (SHAP)"]
            for s in shap[:3]:
                direction = "↑" if s.get("shap", 0) > 0 else "↓"
                lines.append(f"  {direction} {s.get('feature','?')}: val={s.get('value','?')} shap={s.get('shap',0):.3f}")
        lines += [
            "",
            "=" * 40,
            "Generated by Apex-Kinetics SOC Platform v2.0",
            "http://localhost:3000",
        ]
        body = "\n".join(lines)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SMTP_USER
        msg["To"]      = ALERT_EMAIL_TO
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
                s.ehlo()
                s.starttls()
                s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(SMTP_USER, [ALERT_EMAIL_TO], msg.as_string())
        except Exception as e:
            print(f"[NOTIFY] Email send failed: {e}")

    # ── Test helpers ─────────────────────────────────────────────────────────

    def send_test_slack(self) -> str:
        if not self.slack_configured:
            return "not_configured"
        try:
            import httpx
        except ImportError:
            return "failed"
        test_detection = {
            "ip": "203.0.113.42", "label": "port_scan", "confidence": 0.91,
            "risk_score": 88, "action": "blocked", "mitre": {"technique_id": "T1046", "technique": "Network Service Discovery", "tactic": "Discovery"},
        }
        return self._send_slack(test_detection, "test")

    def send_test_email(self) -> str:
        if not self.email_configured:
            return "not_configured"
        test_detection = {
            "ip": "203.0.113.42", "label": "port_scan", "confidence": 0.91,
            "risk_score": 88, "action": "blocked", "mitre": {},
        }
        return self._send_email(test_detection, "test")

    # ── Log ──────────────────────────────────────────────────────────────────

    def _append_log(self, detection: dict, reason: str, slack_st: str, email_st: str) -> None:
        entry = {
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "ip":          detection.get("ip", ""),
            "attack_type": detection.get("label", ""),
            "reason":      reason,
            "slack":       slack_st,
            "email":       email_st,
        }
        with self._log_lock:
            self._log.append(entry)
            if len(self._log) > 50:
                self._log.pop(0)

    def get_log(self) -> list:
        with self._log_lock:
            return list(reversed(self._log))


def _severity_from_risk(risk) -> str:
    if risk is None: return "medium"
    r = float(risk)
    if r > 85: return "critical"
    if r >= 60: return "high"
    if r >= 30: return "medium"
    return "low"


# Module-level singleton
service = NotificationService()
