"""
GeoIP routes — Phase 5A.

GET /api/geo/summary   — top countries + coverage stats
GET /api/geo/attackers — all historical attack points with geo data (for map)
GET /api/geo/{ip}      — single IP lookup (cache-first, live fallback)

Note: /summary and /attackers MUST come before /{ip} to prevent the path
parameter from capturing the literal strings.
"""
import csv

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends

from backend.app.core.auth import require_analyst
from backend.app.core.paths import DETECTIONS_FILE
from backend.app.services.geoip_service import geoip_service, _is_private

router = APIRouter(prefix="/api/geo", tags=["geo"])


def _read_detections_by_ip() -> dict:
    """Read detections.csv; return {ip: {count, last_seen, types{}}} for external IPs."""
    by_ip: dict = {}
    try:
        with open(DETECTIONS_FILE, newline="") as f:
            for row in csv.DictReader(f):
                ip = row.get("ip", "").strip()
                if not ip or _is_private(ip):
                    continue
                if ip not in by_ip:
                    by_ip[ip] = {"count": 0, "last_seen": None, "types": {}}
                by_ip[ip]["count"] += 1
                ts = row.get("timestamp", "")
                if ts and (by_ip[ip]["last_seen"] is None or ts > by_ip[ip]["last_seen"]):
                    by_ip[ip]["last_seen"] = ts
                label = row.get("label", "unknown")
                by_ip[ip]["types"][label] = by_ip[ip]["types"].get(label, 0) + 1
    except FileNotFoundError:
        pass
    except Exception as exc:
        print(f"[GeoIP] detections read error: {exc}")
    return by_ip


def _load_geo_map() -> dict:
    """Load all geo cache entries; return {ip: cache_row}."""
    try:
        from backend.app.core.database import run_async, get_all_geo_cache
        rows = run_async(get_all_geo_cache(), timeout=5)
        return {r["ip"]: r for r in rows}
    except Exception:
        return {}


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/summary")
def geo_summary(_: dict = Depends(require_analyst)):
    by_ip = _read_detections_by_ip()
    geo_map = _load_geo_map()

    geolocated = {ip for ip in by_ip if ip in geo_map}
    total_external = len(by_ip)
    coverage_rate = round(len(geolocated) / total_external, 3) if total_external else 0.0

    # Aggregate attack counts by country (only for IPs we have geo for)
    countries: dict = {}
    try:
        with open(DETECTIONS_FILE, newline="") as f:
            for row in csv.DictReader(f):
                ip = row.get("ip", "").strip()
                geo = geo_map.get(ip)
                if geo is None:
                    continue
                code = geo.get("country_code") or ""
                if not code:
                    continue
                ts = row.get("timestamp", "")
                if code not in countries:
                    countries[code] = {
                        "country_code": code,
                        "country_name": geo.get("country_name") or code,
                        "count": 0,
                        "last_seen": None,
                    }
                countries[code]["count"] += 1
                if ts and (countries[code]["last_seen"] is None or ts > countries[code]["last_seen"]):
                    countries[code]["last_seen"] = ts
    except FileNotFoundError:
        pass
    except Exception as exc:
        print(f"[GeoIP] summary aggregation error: {exc}")

    top_countries = sorted(countries.values(), key=lambda x: x["count"], reverse=True)[:10]

    return {
        "top_countries": top_countries,
        "total_geolocated": len(geolocated),
        "coverage_rate": coverage_rate,
    }


@router.get("/attackers")
def geo_attackers(_: dict = Depends(require_analyst)):
    by_ip  = _read_detections_by_ip()
    geo_map = _load_geo_map()

    result = []
    for ip, data in by_ip.items():
        geo = geo_map.get(ip)
        if geo is None:
            continue
        lat = geo.get("lat")
        lon = geo.get("lon")
        if lat is None or lon is None:
            continue
        most_common = max(data["types"], key=lambda k: data["types"][k], default="unknown")
        result.append({
            "ip":           ip,
            "lat":          lat,
            "lon":          lon,
            "country_code": geo.get("country_code") or "",
            "city":         geo.get("city") or "",
            "attack_type":  most_common,
            "count":        data["count"],
            "last_seen":    data["last_seen"],
        })

    result.sort(key=lambda x: x["count"], reverse=True)
    return result[:500]   # cap to keep response size manageable


@router.get("/{ip}")
def geo_ip_lookup(ip: str, _: dict = Depends(require_analyst)):
    if _is_private(ip):
        raise HTTPException(status_code=400, detail="private or reserved IP")

    # Try cache first (fast synchronous read on background loop)
    cached = geoip_service.lookup_sync_cache_only(ip)
    if cached:
        return {"ip": ip, **cached, "source": "cache"}

    # Live lookup (blocks thread for up to 12 s — acceptable for on-demand endpoint)
    try:
        from backend.app.core.database import run_async
        result = run_async(geoip_service.lookup(ip), timeout=12)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"geo lookup failed: {exc}")

    if result is None:
        raise HTTPException(status_code=404, detail=f"no geo data found for {ip}")

    return {
        "ip":           ip,
        "lat":          result.lat,
        "lon":          result.lon,
        "country_code": result.country_code,
        "country_name": result.country_name,
        "city":         result.city,
        "isp":          result.isp,
        "source":       result.source,
    }
