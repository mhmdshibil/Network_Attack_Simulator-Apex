"""
CVEService — Phase 5C: CISA Known Exploited Vulnerabilities (KEV) feed.

Fetches the public CISA KEV JSON (no auth), caches it in the cve_entries table,
and cross-references live detections against it by attack-type keyword matching.

Runs on the background DB loop (via database.run_async / run_async_bg) so all DB
writes stay on a single loop — consistent with threat_intel_service.
"""
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, date, timedelta
from typing import Optional

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
FETCH_INTERVAL_SECONDS = 24 * 3600   # daily

# attack_type → keywords searched against a CVE's concatenated search_text
ATTACK_KEYWORDS = {
    "sql_injection": ["sql", "database", "mysql", "postgresql", "oracle", "mssql", "phpmyadmin", "injection"],
    "bruteforce":    ["authentication", "login", "ssh", "rdp", "credential", "password", "brute"],
    "malware":       ["remote code execution", "rce", "backdoor", "trojan", "ransomware", "arbitrary code"],
    "port_scan":     ["network", "scanner", "reconnaissance", "discovery"],
    "ddos":          ["denial of service", "dos", "amplification", "flood", "resource exhaustion"],
    # unknown_anomaly handled specially → recent CVEs
}


@dataclass
class CVEMatch:
    cve_id: str
    name: str
    product: str
    relevance: float
    ransomware: bool
    date_added: str

    def as_dict(self) -> dict:
        return asdict(self)


class CVEService:
    def __init__(self):
        self._cache: list = []          # list of cve dicts (search_text lowercased)
        self._last_updated: Optional[datetime] = None

    # ── fetch + store ─────────────────────────────────────────────────────────
    async def fetch_and_store(self) -> int:
        try:
            import httpx
        except ImportError:
            print("[CVE] httpx not installed; cannot fetch KEV feed")
            return 0
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(KEV_URL)
            if r.status_code != 200:
                print(f"[CVE] KEV fetch failed: HTTP {r.status_code}")
                return 0
            data = r.json()
        except Exception as exc:
            print(f"[CVE] KEV fetch error: {exc}")
            return 0

        vulns = data.get("vulnerabilities", [])
        parsed = []
        for v in vulns:
            vendor = v.get("vendorProject", "") or ""
            product = v.get("product", "") or ""
            name = v.get("vulnerabilityName", "") or ""
            desc = v.get("shortDescription", "") or ""
            search_text = " ".join([vendor, product, name, desc]).lower()
            parsed.append({
                "cve_id": v.get("cveID"),
                "vendor_project": vendor,
                "product": product,
                "vulnerability_name": name,
                "date_added": v.get("dateAdded"),
                "short_description": desc,
                "required_action": v.get("requiredAction"),
                "due_date": v.get("dueDate"),
                "known_ransomware": (v.get("knownRansomwareCampaignUse", "").strip().lower() == "known"),
                "search_text": search_text,
            })

        try:
            from backend.app.core.database import upsert_cves
            count = await upsert_cves(parsed)
        except Exception as exc:
            print(f"[CVE] DB upsert error: {exc}")
            return 0

        # refresh in-memory cache
        self._cache = parsed
        self._last_updated = datetime.now(timezone.utc)
        print(f"[CVE] Updated {count} entries from CISA KEV")
        return count

    async def _ensure_cache(self) -> None:
        if self._cache:
            return
        try:
            from backend.app.core.database import get_all_cves
            self._cache = await get_all_cves()
            # normalise search_text to lowercase for matching
            for c in self._cache:
                if c.get("search_text"):
                    c["search_text"] = c["search_text"].lower()
        except Exception:
            self._cache = []

    # ── matching ──────────────────────────────────────────────────────────────
    async def match_detection(self, detection: dict) -> list:
        """Return up to 3 CVEMatch objects for a detection's attack_type."""
        await self._ensure_cache()
        if not self._cache:
            return []

        attack_type = (detection.get("attack_type") or "").lower()

        if attack_type == "unknown_anomaly":
            return self._recent_matches(days=30)

        keywords = ATTACK_KEYWORDS.get(attack_type)
        if not keywords:
            return []

        scored = []
        for c in self._cache:
            text = c.get("search_text") or ""
            hits = sum(1 for kw in keywords if kw in text)
            if hits == 0:
                continue
            relevance = min(1.0, hits / 3.0)   # 3+ keyword hits → full relevance
            if c.get("known_ransomware"):
                relevance = min(1.0, relevance + 0.1)
            scored.append((relevance, c))

        scored.sort(key=lambda t: (t[0], t[1].get("date_added") or ""), reverse=True)
        return [self._to_match(c, rel) for rel, c in scored[:3]]

    def _recent_matches(self, days: int = 30) -> list:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        recent = [c for c in self._cache if (c.get("date_added") or "") >= cutoff]
        recent.sort(key=lambda c: c.get("date_added") or "", reverse=True)
        return [self._to_match(c, 0.5) for c in recent[:3]]

    @staticmethod
    def _to_match(c: dict, relevance: float) -> CVEMatch:
        product = " ".join(filter(None, [c.get("vendor_project"), c.get("product")])).strip()
        return CVEMatch(
            cve_id=c.get("cve_id"),
            name=c.get("vulnerability_name") or "",
            product=product,
            relevance=round(relevance, 3),
            ransomware=bool(c.get("known_ransomware")),
            date_added=c.get("date_added") or "",
        )

    # ── read helpers for the API ──────────────────────────────────────────────
    async def get_recent_cves(self, days: int = 30) -> list:
        try:
            from backend.app.core.database import get_recent_cves
            return await get_recent_cves(days)
        except Exception:
            return []

    async def get_stats(self) -> dict:
        try:
            from backend.app.core.database import get_cve_stats
            return await get_cve_stats()
        except Exception:
            return {
                "total_cves": 0, "last_updated": None, "ransomware_count": 0,
                "recent_30_days": 0, "top_vendors": [],
            }


cve_service = CVEService()


async def cve_fetch_loop() -> None:
    """Fetch on startup, then every 24h. Runs on the background DB loop."""
    # small delay so DB tables are ready
    await asyncio.sleep(2)
    while True:
        try:
            await cve_service.fetch_and_store()
        except Exception as exc:
            print(f"[CVE] fetch loop error: {exc}")
        await asyncio.sleep(FETCH_INTERVAL_SECONDS)
