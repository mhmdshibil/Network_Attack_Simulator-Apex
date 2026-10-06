"""
CampaignService — Phase 5B: attack campaign correlation.

Groups multiple detections from the same source_ip into a single Campaign
entity when any of three correlation rules fire:

  Rule 1 — multi_vector : 3+ distinct attack_types within 10 minutes
  Rule 2 — kill_chain   : 3+ consecutive MITRE kill-chain stages within 30 minutes
  Rule 3 — high_volume  : 10+ detections within 5 minutes

Rule priority (for the campaign's reported type + severity):
  kill_chain > multi_vector > high_volume
kill_chain is "high" severity; the other two are "medium".

Concurrency: process_detection() is always invoked on the single background DB
loop (via database.run_async / run_async_bg from the detection pipeline), so the
in-memory _ip_state dict is only ever touched from one loop — no locking needed.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

# ── Correlation windows (seconds) ────────────────────────────────────────────
MULTI_VECTOR_WINDOW_SECONDS = 600     # Rule 1 — 10 minutes
KILL_CHAIN_WINDOW_SECONDS   = 1800    # Rule 2 — 30 minutes
HIGH_VOLUME_WINDOW_SECONDS  = 300     # Rule 3 — 5 minutes
STATE_RETENTION_SECONDS     = 1800    # keep 30 min of detections per IP
CAMPAIGN_IDLE_SECONDS       = 1800    # complete a campaign after 30 min idle

MULTI_VECTOR_MIN_TYPES = 3
KILL_CHAIN_MIN_STAGES  = 3
HIGH_VOLUME_MIN_COUNT  = 10

# ── Kill-chain stage map: attack_type → (stage_number, stage_name) ────────────
STAGE_MAP = {
    "port_scan":     (1, "Recon"),
    "bruteforce":    (2, "Access"),
    "sql_injection": (2, "Access"),
    "malware":       (3, "Execute"),
    "ddos":          (4, "Impact"),
}
STAGE_ORDER = ["Recon", "Access", "Execute", "Impact"]


def _parse_ts(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _longest_consecutive_run(stage_numbers: set) -> int:
    """Length of the longest run of consecutive integers in the set."""
    if not stage_numbers:
        return 0
    best = 1
    for n in stage_numbers:
        if (n - 1) not in stage_numbers:      # start of a run
            length = 1
            while (n + length) in stage_numbers:
                length += 1
            best = max(best, length)
    return best


class CampaignService:
    def __init__(self):
        # source_ip → {"detections": [...], "campaign_id": str|None, "stage": int}
        self._ip_state: dict = {}

    # ── window helpers ────────────────────────────────────────────────────────
    @staticmethod
    def _within(dets: list, now: datetime, seconds: int) -> list:
        cutoff = now - timedelta(seconds=seconds)
        return [d for d in dets if _parse_ts(d["timestamp"]) >= cutoff]

    def _evaluate_rules(self, dets: list, now: datetime) -> Optional[dict]:
        """Return the highest-priority triggered rule's descriptor, or None."""
        # Rule 2 — kill chain (highest priority)
        kc = self._within(dets, now, KILL_CHAIN_WINDOW_SECONDS)
        stage_nums = {STAGE_MAP[d["attack_type"]][0] for d in kc if d["attack_type"] in STAGE_MAP}
        kill_run = _longest_consecutive_run(stage_nums)

        # Rule 1 — multi-vector
        mv = self._within(dets, now, MULTI_VECTOR_WINDOW_SECONDS)
        distinct_types = {d["attack_type"] for d in mv}

        # Rule 3 — high volume
        hv = self._within(dets, now, HIGH_VOLUME_WINDOW_SECONDS)

        if kill_run >= KILL_CHAIN_MIN_STAGES:
            return {"type": "kill_chain", "severity": "high"}
        if len(distinct_types) >= MULTI_VECTOR_MIN_TYPES:
            return {"type": "multi_vector", "severity": "medium"}
        if len(hv) >= HIGH_VOLUME_MIN_COUNT:
            return {"type": "high_volume", "severity": "medium"}
        return None

    def _campaign_fields(self, ip: str, dets: list, now: datetime, rule: dict) -> dict:
        """Build the persisted campaign field set from the current window."""
        window = self._within(dets, now, STATE_RETENTION_SECONDS)
        # attack_sequence: distinct types in order of first appearance
        seq: list = []
        for d in window:
            if d["attack_type"] not in seq:
                seq.append(d["attack_type"])
        # distinct kill-chain stage names, in canonical order
        stage_names = {STAGE_MAP[d["attack_type"]][1] for d in window if d["attack_type"] in STAGE_MAP}
        mitre_stages = [s for s in STAGE_ORDER if s in stage_names]
        detection_ids = [d["id"] for d in window if d.get("id")]
        started = min((_parse_ts(d["timestamp"]) for d in window), default=now)
        return {
            "source_ip": ip,
            "campaign_type": rule["type"],
            "severity": rule["severity"],
            "stage_count": len(mitre_stages),
            "attack_types": seq,
            "detection_ids": detection_ids,
            "mitre_stages": mitre_stages,
            "total_detections": len(window),
            "started_at": started.isoformat(),
            "last_seen_at": now.isoformat(),
            "geo_country": self._geo_country(ip),
        }

    @staticmethod
    def _geo_country(ip: str) -> Optional[str]:
        try:
            from backend.app.services.geoip_service import geoip_service as _gs
            geo = _gs.lookup_sync_cache_only(ip)
            if geo:
                return geo.get("country_name") or geo.get("country_code")
        except Exception:
            pass
        return None

    # ── public entry point ────────────────────────────────────────────────────
    async def process_detection(self, detection: dict) -> Optional[dict]:
        """
        Called after every non-normal detection. Updates the per-IP window,
        evaluates the three rules, and creates/updates a campaign + broadcasts
        a campaign_update when a rule fires. Returns the campaign dict or None.
        """
        ip = detection.get("source_ip")
        attack_type = detection.get("attack_type")
        if not ip or not attack_type or attack_type == "normal":
            return None

        now = datetime.now(timezone.utc)
        state = self._ip_state.setdefault(ip, {"detections": [], "campaign_id": None, "stage": 0})

        # 1. add + 2. prune to 30-minute retention window
        state["detections"].append({
            "id": detection.get("id"),
            "attack_type": attack_type,
            "timestamp": detection.get("timestamp") or now.isoformat(),
            "confidence": detection.get("confidence"),
            "risk_score": detection.get("risk_score"),
            "mitre_tactic": detection.get("mitre_tactic"),
        })
        state["detections"] = self._within(state["detections"], now, STATE_RETENTION_SECONDS)

        # Rehydrate campaign_id after a restart (in-memory state was lost)
        if state["campaign_id"] is None:
            try:
                from backend.app.core.database import get_active_campaign_by_ip
                existing = await get_active_campaign_by_ip(ip)
                if existing:
                    state["campaign_id"] = existing["id"]
            except Exception:
                pass

        # 3. evaluate rules
        rule = self._evaluate_rules(state["detections"], now)
        if rule is None and state["campaign_id"] is None:
            return None   # nothing to report yet

        try:
            from backend.app.core.database import create_campaign, update_campaign
        except Exception:
            return None

        # If no rule currently fires but a campaign is already active, still
        # update its last_seen/detection count (keeps it "alive").
        effective_rule = rule or self._current_rule(state)
        fields = self._campaign_fields(ip, state["detections"], now, effective_rule)

        campaign: Optional[dict] = None
        try:
            if state["campaign_id"] is None:
                # 4. create new campaign
                campaign = await create_campaign(**fields)
                state["campaign_id"] = campaign["id"]
            else:
                # 5. update existing campaign (recompute type/severity/stages)
                campaign = await update_campaign(state["campaign_id"], **{
                    "campaign_type": fields["campaign_type"],
                    "severity": fields["severity"],
                    "stage_count": fields["stage_count"],
                    "attack_types": fields["attack_types"],
                    "detection_ids": fields["detection_ids"],
                    "mitre_stages": fields["mitre_stages"],
                    "total_detections": fields["total_detections"],
                    "last_seen_at": fields["last_seen_at"],
                    "geo_country": fields["geo_country"],
                })
                # Campaign may have been completed/purged — recreate if missing
                if campaign is None:
                    campaign = await create_campaign(**fields)
                    state["campaign_id"] = campaign["id"]
        except Exception as exc:
            print(f"[CAMPAIGN] persistence error: {exc}")
            return None

        state["stage"] = fields["stage_count"]

        # 6. broadcast
        self._broadcast(campaign, fields["attack_types"])
        return campaign

    def _current_rule(self, state: dict) -> dict:
        """Fallback rule descriptor for an already-active campaign when no rule
        currently fires (e.g. a lone late detection). Keeps existing type."""
        return {"type": "multi_vector", "severity": "medium"}

    @staticmethod
    def _broadcast(campaign: dict, attack_sequence: list) -> None:
        if not campaign:
            return
        try:
            from backend.app.services.ws_manager import manager as ws_manager
            ws_manager.broadcast_sync({
                "type": "campaign_update",
                "campaign_id": campaign["id"],
                "source_ip": campaign["source_ip"],
                "campaign_type": campaign["campaign_type"],
                "stage_count": campaign["stage_count"],
                "attack_sequence": attack_sequence,
                "attack_types": campaign["attack_types"],
                "mitre_stages": campaign["mitre_stages"],
                "severity": campaign["severity"],
                "status": campaign["status"],
                "total_detections": campaign["total_detections"],
                "geo_country": campaign.get("geo_country"),
                "started_at": campaign.get("started_at"),
                "last_seen_at": campaign.get("last_seen_at"),
            })
        except Exception as exc:
            print(f"[CAMPAIGN] broadcast skipped: {exc}")

        # Webhook delivery (Phase 6C)
        try:
            from backend.app.services.webhook_service import webhook_service as _wh
            from backend.app.core.database import run_async_bg
            run_async_bg(_wh.deliver("campaign", campaign))
        except Exception:
            pass

    # ── background sweeper ─────────────────────────────────────────────────────
    async def sweep_completed(self) -> None:
        """Mark idle campaigns completed and broadcast the transition."""
        try:
            from backend.app.core.database import complete_stale_campaigns
            completed = await complete_stale_campaigns(CAMPAIGN_IDLE_SECONDS)
        except Exception:
            return
        for c in completed:
            # drop the in-memory link so a future detection starts a fresh campaign
            st = self._ip_state.get(c["source_ip"])
            if st and st.get("campaign_id") == c["id"]:
                st["campaign_id"] = None
            self._broadcast(c, c.get("attack_types", []))


campaign_service = CampaignService()


async def campaign_sweep_loop(interval_seconds: int = 60) -> None:
    """Periodic task (started from app lifespan) that completes idle campaigns."""
    import asyncio
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await campaign_service.sweep_completed()
        except Exception as exc:
            print(f"[CAMPAIGN] sweep error: {exc}")
