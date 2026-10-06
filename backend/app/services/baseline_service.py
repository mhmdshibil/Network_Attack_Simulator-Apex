"""
BaselineService — Phase 5D: per-deployment network baseline learning.

Learns what "normal" traffic looks like for THIS deployment, per hour-of-day,
using Welford's online algorithm (numerically stable running mean/variance with
no need to store raw samples). Once an hour has MIN_SAMPLES observations it goes
"active" and traffic that deviates > DEVIATION_THRESHOLD sigma on 2+ features is
flagged as a soft "baseline_deviation" alert.

Fully synchronous and fast (dict math only). Persisted to disk every 5 minutes
so the learned baseline survives restarts.
"""
import json
import math
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from backend.app.ml.feature_engineering import FEATURE_COLUMNS
from backend.app.core.paths import BASELINE_FILE, BASELINE_DIR

MIN_SAMPLES = 100
DEVIATION_THRESHOLD = 3.0
HIGH_Z = 5.0


def _hour_label(hour: int) -> str:
    h = hour % 24
    if h == 0:
        return "12am"
    if h == 12:
        return "12pm"
    if h < 12:
        return f"{h}am"
    return f"{h - 12}pm"


class BaselineService:
    def __init__(self):
        # hour(0-23) → feature → {"mean": float, "M2": float, "n": int}
        self._stats: dict = {h: {f: {"mean": 0.0, "M2": 0.0, "n": 0} for f in FEATURE_COLUMNS}
                             for h in range(24)}
        self._samples_per_hour: dict = {h: 0 for h in range(24)}
        self._total_samples = 0
        self._alerts: deque = deque(maxlen=100)

    # ── learning ──────────────────────────────────────────────────────────────
    def update(self, detection: dict) -> None:
        """Update running stats for the current hour. Called for every detection."""
        hour = self._hour_of(detection)
        any_feature = False
        for f in FEATURE_COLUMNS:
            v = detection.get(f)
            if v is None:
                continue
            try:
                x = float(v)
            except (TypeError, ValueError):
                continue
            s = self._stats[hour][f]
            s["n"] += 1
            delta = x - s["mean"]
            s["mean"] += delta / s["n"]
            delta2 = x - s["mean"]
            s["M2"] += delta * delta2
            any_feature = True
        if any_feature:
            self._samples_per_hour[hour] += 1
            self._total_samples += 1

    # ── deviation check ───────────────────────────────────────────────────────
    def _std(self, s: dict) -> float:
        return math.sqrt(s["M2"] / (s["n"] - 1)) if s["n"] > 1 else 0.0

    def check_deviation(self, detection: dict) -> Optional[dict]:
        """Return a baseline_deviation alert if 2+ features deviate > threshold σ,
        but only once the current hour is 'active' (>= MIN_SAMPLES)."""
        hour = self._hour_of(detection)
        if self._samples_per_hour[hour] < MIN_SAMPLES:
            return None   # still learning this hour

        deviating = []
        max_z = 0.0
        for f in FEATURE_COLUMNS:
            v = detection.get(f)
            if v is None:
                continue
            try:
                x = float(v)
            except (TypeError, ValueError):
                continue
            s = self._stats[hour][f]
            std = self._std(s)
            if std <= 0:
                continue
            z = (x - s["mean"]) / std
            if abs(z) > DEVIATION_THRESHOLD:
                deviating.append({
                    "feature": f,
                    "value": round(x, 3),
                    "baseline_mean": round(s["mean"], 3),
                    "z_score": round(z, 2),
                })
                max_z = max(max_z, abs(z))

        if len(deviating) < 2:
            return None

        severity = "high" if max_z > HIGH_Z else "medium"
        ip = detection.get("source_ip") or detection.get("ip") or "unknown"
        alert = {
            "alert_type": "baseline_deviation",
            "source_ip": ip,
            "hour": hour,
            "deviating_features": deviating,
            "severity": severity,
            "message": f"Traffic from {ip} deviates significantly from {_hour_label(hour)} baseline",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._alerts.appendleft(alert)
        return alert

    # ── status / reads ────────────────────────────────────────────────────────
    def _hour_of(self, detection: dict) -> int:
        ts = detection.get("timestamp")
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return dt.astimezone(timezone.utc).hour
            except Exception:
                pass
        return datetime.now(timezone.utc).hour

    def _hour_status(self, hour: int) -> str:
        return "active" if self._samples_per_hour[hour] >= MIN_SAMPLES else "learning"

    def get_baseline_status(self) -> dict:
        hours_active = [h for h in range(24) if self._samples_per_hour[h] >= MIN_SAMPLES]
        hours_learning = [h for h in range(24) if 0 < self._samples_per_hour[h] < MIN_SAMPLES]
        return {
            "status": "active" if hours_active else "learning",
            "samples_per_hour": dict(self._samples_per_hour),
            "min_samples_required": MIN_SAMPLES,
            "hours_active": hours_active,
            "hours_learning": hours_learning,
            "total_samples": self._total_samples,
            "deviation_threshold": DEVIATION_THRESHOLD,
        }

    def get_hourly_stats(self, hour: int) -> dict:
        hour = hour % 24
        out = {}
        for f in FEATURE_COLUMNS:
            s = self._stats[hour][f]
            out[f] = {
                "mean": round(s["mean"], 3),
                "std": round(self._std(s), 3),
                "samples": s["n"],
            }
        return {
            "hour": hour,
            "status": self._hour_status(hour),
            "samples": self._samples_per_hour[hour],
            "features": out,
        }

    def get_chart_data(self) -> dict:
        hours = list(range(24))
        features = {}
        for f in FEATURE_COLUMNS:
            means, stds = [], []
            for h in hours:
                s = self._stats[h][f]
                means.append(round(s["mean"], 3))
                stds.append(round(self._std(s), 3))
            features[f] = {"means": means, "stds": stds}
        return {"hours": hours, "features": features}

    def get_alerts(self) -> list:
        return list(self._alerts)

    def reset(self) -> None:
        self._stats = {h: {f: {"mean": 0.0, "M2": 0.0, "n": 0} for f in FEATURE_COLUMNS}
                       for h in range(24)}
        self._samples_per_hour = {h: 0 for h in range(24)}
        self._total_samples = 0
        self._alerts.clear()
        try:
            if BASELINE_FILE.exists():
                BASELINE_FILE.unlink()
        except Exception:
            pass

    # ── persistence ───────────────────────────────────────────────────────────
    def export_baseline(self) -> dict:
        return {
            "stats": self._stats,
            "samples_per_hour": self._samples_per_hour,
            "total_samples": self._total_samples,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

    def load_baseline(self, data: dict) -> None:
        try:
            raw = data.get("stats", {})
            # JSON keys are strings — coerce hour keys back to int
            for h in range(24):
                hd = raw.get(str(h)) or raw.get(h) or {}
                for f in FEATURE_COLUMNS:
                    if f in hd:
                        self._stats[h][f] = {
                            "mean": float(hd[f].get("mean", 0.0)),
                            "M2": float(hd[f].get("M2", 0.0)),
                            "n": int(hd[f].get("n", 0)),
                        }
            sph = data.get("samples_per_hour", {})
            for h in range(24):
                self._samples_per_hour[h] = int(sph.get(str(h)) or sph.get(h) or 0)
            self._total_samples = int(data.get("total_samples", 0))
        except Exception as exc:
            print(f"[BASELINE] load error: {exc}")

    def save_to_disk(self) -> None:
        try:
            BASELINE_DIR.mkdir(parents=True, exist_ok=True)
            BASELINE_FILE.write_text(json.dumps(self.export_baseline()))
        except Exception as exc:
            print(f"[BASELINE] save error: {exc}")

    def load_from_disk(self) -> None:
        try:
            if BASELINE_FILE.exists():
                self.load_baseline(json.loads(BASELINE_FILE.read_text()))
                print(f"[BASELINE] loaded {self._total_samples} samples from disk")
        except Exception as exc:
            print(f"[BASELINE] load_from_disk error: {exc}")


baseline_service = BaselineService()


async def baseline_persist_loop(interval_seconds: int = 300) -> None:
    """Persist the baseline to disk every 5 minutes."""
    import asyncio
    while True:
        await asyncio.sleep(interval_seconds)
        baseline_service.save_to_disk()
