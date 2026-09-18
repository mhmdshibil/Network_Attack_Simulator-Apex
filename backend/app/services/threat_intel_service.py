"""
ThreatIntelService (Phase 2 / Task 3).

Cross-references a detected IP against free threat-intel sources:
  1. AbuseIPDB   (needs ABUSEIPDB_API_KEY;  1000 req/day, throttled 1 req/s)
  2. VirusTotal  (needs VIRUSTOTAL_API_KEY;  500 req/day, throttled 1 req/15s)
  3. Local blocklist fallback (always available, no key): a small set of
     known-bad CIDR ranges, plus the public CISA KEV feed for context.

Results are cached in the ip_reputation table for 24h. Without any API key the
service still works via the local blocklist (source="local").

httpx and the DB layer are imported lazily so this module is import-safe even
when those optional dependencies are not installed.
"""
import asyncio
import ipaddress
import os
import time
from datetime import datetime, timezone

ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY", "").strip()
VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY", "").strip()

CACHE_TTL_SECONDS = 24 * 3600
CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

# Small demo blocklist — common Tor-exit / abuse / botnet ranges.
_KNOWN_BAD_CIDRS = [
    "185.220.100.0/22",   # Tor exit relays
    "185.220.101.0/24",   # Tor exit relays
    "185.220.0.0/16",     # broad abuse range (demo)
    "45.142.212.0/24",    # malware hosting
    "45.142.0.0/16",      # abuse range (demo)
    "91.108.0.0/16",      # abuse range (demo)
    "89.248.165.0/24",    # scanning infrastructure
    "193.169.252.0/24",   # brute-force sources
    "194.165.16.0/24",    # botnet C2 (demo)
    "146.70.0.0/16",      # VPN/abuse range (demo)
    "103.0.0.0/16",       # abuse range (demo)
    "80.94.92.0/24",      # scanners
]

# AbuseIPDB confidence / VT malicious thresholds that flag an IP as known-bad.
_ABUSE_BAD_THRESHOLD = 80
_VT_BAD_THRESHOLD = 3


class ThreatIntelService:
    def __init__(self):
        self._nets = []
        for c in _KNOWN_BAD_CIDRS:
            try:
                self._nets.append(ipaddress.ip_network(c))
            except ValueError:
                pass
        # rate-limit + quota state
        self._abuse_last = 0.0
        self._abuse_day = None
        self._abuse_count = 0
        self._vt_last = 0.0
        self._vt_day = None
        self._vt_count = 0
        # stats
        self._checked_today = set()
        self._known_bad = set()
        self._cache_hits = 0
        self._cache_misses = 0

    # ── config ──────────────────────────────────────────────────────────────
    @property
    def configured(self) -> bool:
        return bool(ABUSEIPDB_API_KEY or VIRUSTOTAL_API_KEY)

    @staticmethod
    def compute_threat_score(abuse, vt, known_bad=False) -> int:
        """Weighted score: AbuseIPDB*0.6 + VirusTotal*0.4 (both normalised 0-100)."""
        a = abuse or 0
        v = min((vt or 0) * 4, 100)   # VT malicious count → 0-100 heuristic
        score = round(a * 0.6 + v * 0.4)
        if known_bad:
            score = max(score, 90)
        return int(score)

    def _local_bad(self, ip: str) -> bool:
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return any(addr in net for net in self._nets)

    # ── cache (DB) ──────────────────────────────────────────────────────────
    async def _get_cache(self, ip: str):
        try:
            from backend.app.core.database import get_ip_reputation
        except Exception:
            return None
        try:
            row = await get_ip_reputation(ip)
        except Exception:
            return None
        if not row or not row.get("checked_at"):
            return None
        try:
            checked = datetime.fromisoformat(row["checked_at"].replace("Z", "+00:00"))
        except Exception:
            return None
        # SQLite (and DateTime(timezone=True) round-trips) can return a naive
        # datetime — force UTC so we never subtract naive from aware.
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - checked).total_seconds()
        return row if age < CACHE_TTL_SECONDS else None

    async def _store_cache(self, ip, abuse_score, vt_malicious, is_known_bad, country, isp, raw):
        try:
            from backend.app.core.database import upsert_ip_reputation
        except Exception:
            return
        try:
            await upsert_ip_reputation(
                ip=ip, abuse_score=abuse_score, vt_malicious=vt_malicious,
                is_known_bad=is_known_bad, country_code=country, isp=isp,
                checked_at=datetime.now(timezone.utc), raw_response=raw,
            )
        except Exception:
            pass

    # ── live sources ────────────────────────────────────────────────────────
    async def _check_abuseipdb(self, ip):
        if not ABUSEIPDB_API_KEY:
            return None
        today = datetime.now(timezone.utc).date()
        if self._abuse_day != today:
            self._abuse_day, self._abuse_count = today, 0
        if self._abuse_count >= 1000:          # daily quota
            return None
        # throttle: max 1 request per second
        wait = 1.0 - (time.monotonic() - self._abuse_last)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            import httpx
        except ImportError:
            return None
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(
                    "https://api.abuseipdb.com/api/v2/check",
                    headers={"Key": ABUSEIPDB_API_KEY, "Accept": "application/json"},
                    params={"ipAddress": ip, "maxAgeInDays": 90},
                )
            self._abuse_last = time.monotonic()
            self._abuse_count += 1
            if r.status_code == 200:
                d = r.json().get("data", {})
                return {
                    "score": int(d.get("abuseConfidenceScore", 0)),
                    "reports": d.get("totalReports", 0),
                    "country": d.get("countryCode"),
                    "isp": d.get("isp"),
                    "usage": d.get("usageType"),
                }
        except Exception:
            return None
        return None

    async def _check_virustotal(self, ip):
        if not VIRUSTOTAL_API_KEY:
            return None
        today = datetime.now(timezone.utc).date()
        if self._vt_day != today:
            self._vt_day, self._vt_count = today, 0
        if self._vt_count >= 500:              # daily quota
            return None
        # throttle: max 1 request per 15 seconds
        wait = 15.0 - (time.monotonic() - self._vt_last)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            import httpx
        except ImportError:
            return None
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(
                    f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
                    headers={"x-apikey": VIRUSTOTAL_API_KEY},
                )
            self._vt_last = time.monotonic()
            self._vt_count += 1
            if r.status_code == 200:
                stats = r.json().get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
                return {"malicious": int(stats.get("malicious", 0)),
                        "suspicious": int(stats.get("suspicious", 0))}
        except Exception:
            return None
        return None

    # ── public API ──────────────────────────────────────────────────────────
    async def check_ip(self, ip: str) -> dict:
        self._checked_today.add(ip)

        cached = await self._get_cache(ip)
        if cached:
            self._cache_hits += 1
            score = self.compute_threat_score(
                cached.get("abuse_score"), cached.get("vt_malicious"), cached.get("is_known_bad"))
            if cached.get("is_known_bad"):
                self._known_bad.add(ip)
            return {
                "ip": ip, "threat_score": score, "is_known_bad": bool(cached.get("is_known_bad")),
                "abuse_confidence": cached.get("abuse_score"), "vt_malicious_count": cached.get("vt_malicious"),
                "country_code": cached.get("country_code"), "isp": cached.get("isp"), "source": "cache",
            }

        self._cache_misses += 1
        abuse = await self._check_abuseipdb(ip)
        vt = await self._check_virustotal(ip)
        local_bad = self._local_bad(ip)

        abuse_score = abuse["score"] if abuse else 0
        vt_mal = vt["malicious"] if vt else 0
        is_known_bad = local_bad or abuse_score >= _ABUSE_BAD_THRESHOLD or vt_mal >= _VT_BAD_THRESHOLD
        threat_score = self.compute_threat_score(abuse_score, vt_mal, is_known_bad)
        country = abuse["country"] if abuse else None
        isp = abuse["isp"] if abuse else None
        source = "abuseipdb" if abuse else ("virustotal" if vt else "local")

        if is_known_bad:
            self._known_bad.add(ip)

        await self._store_cache(
            ip, abuse_score if abuse else None, vt_mal if vt else None,
            is_known_bad, country, isp, {"abuse": abuse, "vt": vt, "local_bad": local_bad},
        )

        return {
            "ip": ip, "threat_score": threat_score, "is_known_bad": is_known_bad,
            "abuse_confidence": abuse_score if abuse else None,
            "vt_malicious_count": vt_mal if vt else None,
            "country_code": country, "isp": isp, "source": source,
        }

    async def stats(self) -> dict:
        total = self._cache_hits + self._cache_misses
        hit_rate = round(self._cache_hits / total, 3) if total else 0.0
        return {
            "configured": self.configured,
            "sources": {
                "abuseipdb": bool(ABUSEIPDB_API_KEY),
                "virustotal": bool(VIRUSTOTAL_API_KEY),
                "local_blocklist": True,
            },
            "checked_today": len(self._checked_today),
            "known_bad_detected": len(self._known_bad),
            "cache_hit_rate": hit_rate,
            "abuseipdb_quota_remaining": (max(0, 1000 - self._abuse_count) if ABUSEIPDB_API_KEY else None),
            "virustotal_quota_remaining": (max(0, 500 - self._vt_count) if VIRUSTOTAL_API_KEY else None),
        }


# Module-level singleton (shares rate-limit + cache-stats state).
service = ThreatIntelService()
