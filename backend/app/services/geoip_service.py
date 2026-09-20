"""
GeoIPService — Phase 5A.

Two-tier lookup:
  Tier 1 — geoip2 + local GeoLite2-City.mmdb (fast, no network, no rate limit)
  Tier 2 — ip-api.com fallback (free, no key needed, 45 req/min cap)

Cache: geoip_cache DB table, 7-day TTL.
Private/reserved IPs always return None immediately.

Usage in sync code (detection_service hot path):
    geo = geoip_service.lookup_sync_cache_only(ip)   # fast, cache only
    run_async_bg(geoip_service.lookup(ip))            # populate cache in background

Usage in async routes:
    result = await geoip_service.lookup(ip)
"""
import asyncio
import ipaddress
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional

GEOIP_DB_PATH = os.getenv("GEOIP_DB_PATH", "data/geoip/GeoLite2-City.mmdb")
_IPAPI_URL = "http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,lat,lon,isp,org"
_CACHE_TTL = 7 * 24 * 3600   # 7 days
_API_INTERVAL = 1.5           # seconds between ip-api.com calls (max 45/min)

_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),  # shared address space
]


def _is_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return addr.is_private or addr.is_loopback or addr.is_link_local or any(
        addr in net for net in _PRIVATE_NETS
    )


@dataclass
class GeoIPResult:
    lat: float
    lon: float
    country_code: str
    country_name: str
    city: str
    isp: str
    source: str   # "local" | "api" | "cache"

    def as_dict(self) -> dict:
        return asdict(self)


class GeoIPService:
    def __init__(self):
        self._reader       = None
        self._reader_tried = False
        self._last_api_ts  = 0.0

    # ── Tier 1: local MaxMind DB ─────────────────────────────────────────────

    def _get_reader(self):
        if self._reader_tried:
            return self._reader
        self._reader_tried = True
        try:
            import geoip2.database  # optional dependency
            if os.path.exists(GEOIP_DB_PATH):
                self._reader = geoip2.database.Reader(GEOIP_DB_PATH)
                print(f"[GeoIP] local DB loaded: {GEOIP_DB_PATH}")
            else:
                print(f"[GeoIP] local DB not found ({GEOIP_DB_PATH}); using ip-api.com fallback")
        except ImportError:
            print("[GeoIP] geoip2 not installed; using ip-api.com fallback")
        return self._reader

    def _lookup_local(self, ip: str) -> Optional[GeoIPResult]:
        reader = self._get_reader()
        if reader is None:
            return None
        try:
            r = reader.city(ip)
            return GeoIPResult(
                lat=float(r.location.latitude  or 0),
                lon=float(r.location.longitude or 0),
                country_code=str(r.country.iso_code or ""),
                country_name=str(r.country.name    or ""),
                city=str(r.city.name or ""),
                isp=str(getattr(r.traits, "isp", None) or getattr(r.traits, "organization", None) or ""),
                source="local",
            )
        except Exception:
            return None

    # ── Tier 2: ip-api.com fallback ─────────────────────────────────────────

    async def _lookup_api(self, ip: str) -> Optional[GeoIPResult]:
        wait = _API_INTERVAL - (time.monotonic() - self._last_api_ts)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_api_ts = time.monotonic()
        try:
            import httpx
        except ImportError:
            return None
        try:
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get(_IPAPI_URL.format(ip=ip))
            d = r.json()
            if d.get("status") != "success":
                return None
            return GeoIPResult(
                lat=float(d.get("lat") or 0),
                lon=float(d.get("lon") or 0),
                country_code=str(d.get("countryCode") or ""),
                country_name=str(d.get("country")     or ""),
                city=str(d.get("city") or ""),
                isp=str(d.get("isp") or d.get("org") or ""),
                source="api",
            )
        except Exception:
            return None

    # ── Cache helpers ────────────────────────────────────────────────────────

    async def _from_cache(self, ip: str) -> Optional[GeoIPResult]:
        try:
            from backend.app.core.database import get_geo_cache
            row = await get_geo_cache(ip)
        except Exception:
            return None
        if row is None:
            return None
        cached_at = row.get("cached_at")
        try:
            if isinstance(cached_at, str):
                cached_at = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
            if cached_at and cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=timezone.utc)
            if cached_at and (datetime.now(timezone.utc) - cached_at).total_seconds() > _CACHE_TTL:
                return None
        except Exception:
            return None
        return GeoIPResult(
            lat=float(row.get("lat") or 0),
            lon=float(row.get("lon") or 0),
            country_code=str(row.get("country_code") or ""),
            country_name=str(row.get("country_name") or ""),
            city=str(row.get("city")    or ""),
            isp=str(row.get("isp")      or ""),
            source="cache",
        )

    async def _store_cache(self, ip: str, result: GeoIPResult) -> None:
        try:
            from backend.app.core.database import upsert_geo_cache
            await upsert_geo_cache(
                ip=ip,
                lat=result.lat,
                lon=result.lon,
                country_code=result.country_code,
                country_name=result.country_name,
                city=result.city,
                isp=result.isp,
                source=result.source,
                cached_at=datetime.now(timezone.utc),
            )
        except Exception:
            pass

    # ── Public API ───────────────────────────────────────────────────────────

    async def lookup(self, ip: str) -> Optional[GeoIPResult]:
        """Full lookup: cache → local DB → ip-api.com. Stores result in cache."""
        if _is_private(ip):
            return None

        cached = await self._from_cache(ip)
        if cached is not None:
            return cached

        result = self._lookup_local(ip) or await self._lookup_api(ip)
        if result is not None:
            await self._store_cache(ip, result)
        return result

    def lookup_sync_cache_only(self, ip: str) -> Optional[dict]:
        """
        Synchronous, cache-only lookup for the detection hot path.
        Runs the DB read on the background event loop (non-blocking from caller's
        perspective). Returns a plain dict or None. Never makes network calls.
        """
        if _is_private(ip):
            return None
        try:
            from backend.app.core.database import run_async, get_geo_cache
            row = run_async(get_geo_cache(ip), timeout=1)
        except Exception:
            return None
        if row is None:
            return None
        # Validate TTL
        try:
            cached_at = row.get("cached_at")
            if isinstance(cached_at, str):
                cached_at = datetime.fromisoformat(cached_at.replace("Z", "+00:00"))
            if cached_at:
                if cached_at.tzinfo is None:
                    cached_at = cached_at.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - cached_at).total_seconds() > _CACHE_TTL:
                    return None
        except Exception:
            return None
        return {
            "lat":          row.get("lat"),
            "lon":          row.get("lon"),
            "country_code": row.get("country_code"),
            "country_name": row.get("country_name"),
            "city":         row.get("city"),
            "isp":          row.get("isp"),
        }


# Module-level singleton — shares rate-limit state across the process.
geoip_service = GeoIPService()
