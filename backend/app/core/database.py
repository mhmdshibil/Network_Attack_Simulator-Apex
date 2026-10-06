"""
Async database layer — SQLAlchemy 2.0 (Phase 2).

PostgreSQL is the primary sink in production; SQLite is the zero-setup default
for local dev (no Docker required). The CSV/JSONL files remain the fallback —
every DB write is fire-and-forget and guarded, so a DB failure (or the DB deps
not being installed at all) never breaks a detection.

Design note — sync pipeline ↔ async engine:
  The detection pipeline is synchronous (runs in a worker thread), but the spec
  calls for an async engine (asyncpg / aiosqlite). asyncpg connections are bound
  to the event loop that created them, so we run ALL async DB work on a single
  dedicated background event loop (started lazily in a daemon thread). Sync
  callers use run_async()/run_async_bg() to submit coroutines to it. This keeps
  every DB connection on one loop and avoids cross-loop asyncpg errors.

  get_db() is provided per spec for future async routes; the current routes and
  the pipeline funnel through the background-loop helpers instead.
"""
import asyncio
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, func, select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ── Config ──────────────────────────────────────────────────────────────────
# Default: SQLite so migrations + dual-write work locally without PostgreSQL.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./apex.db")


class Base(DeclarativeBase):
    pass


# ── ip_reputation cache table (Threat Intel — Phase 2 / Task 3) ─────────────
class IpReputation(Base):
    __tablename__ = "ip_reputation"

    ip:            Mapped[str]            = mapped_column(String(45), primary_key=True)
    abuse_score:   Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vt_malicious:  Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_known_bad:  Mapped[bool]          = mapped_column(Boolean, default=False)
    country_code:  Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    isp:           Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    checked_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_response:  Mapped[Optional[dict]]     = mapped_column(JSON, nullable=True)


# ── geoip_cache table (Phase 5A / GeoIP) ────────────────────────────────────
class GeoIPCache(Base):
    __tablename__ = "geoip_cache"

    ip:           Mapped[str]              = mapped_column(String(45), primary_key=True)
    lat:          Mapped[Optional[float]]  = mapped_column(Float, nullable=True)
    lon:          Mapped[Optional[float]]  = mapped_column(Float, nullable=True)
    country_code: Mapped[Optional[str]]    = mapped_column(String(3),   nullable=True)
    country_name: Mapped[Optional[str]]    = mapped_column(String(100), nullable=True)
    city:         Mapped[Optional[str]]    = mapped_column(String(100), nullable=True)
    isp:          Mapped[Optional[str]]    = mapped_column(String(200), nullable=True)
    source:       Mapped[Optional[str]]    = mapped_column(String(20),  nullable=True)
    cached_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Engine / session (lazy) ─────────────────────────────────────────────────
_engine = None
_sessionmaker: Optional[async_sessionmaker] = None


def _init_engine():
    global _engine, _sessionmaker
    if _engine is None:
        kwargs: dict = {"echo": False, "future": True}
        # QueuePool sizing only applies to server databases, not SQLite.
        if not DATABASE_URL.startswith("sqlite"):
            kwargs.update(pool_size=5, max_overflow=10)
        _engine = create_async_engine(DATABASE_URL, **kwargs)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
    return _engine, _sessionmaker


# ── Background event loop (owns the engine) ─────────────────────────────────
_bg_loop: Optional[asyncio.AbstractEventLoop] = None
_bg_lock = threading.Lock()


def _bg() -> asyncio.AbstractEventLoop:
    global _bg_loop
    if _bg_loop is None:
        with _bg_lock:
            if _bg_loop is None:
                loop = asyncio.new_event_loop()
                threading.Thread(target=loop.run_forever, daemon=True, name="apex-db-loop").start()
                _bg_loop = loop
    return _bg_loop


def run_async(coro, timeout: float = 10):
    """Submit a coroutine to the background DB loop and wait for its result."""
    return asyncio.run_coroutine_threadsafe(coro, _bg()).result(timeout=timeout)


def run_async_bg(coro) -> None:
    """Fire-and-forget a coroutine on the background DB loop (non-blocking)."""
    asyncio.run_coroutine_threadsafe(_guarded(coro), _bg())


async def _guarded(coro):
    try:
        await coro
    except Exception as exc:  # never surface DB errors to the pipeline
        print(f"[DB] write failed (CSV/JSONL fallback retains the record): {exc}")


# ── Schema lifecycle ────────────────────────────────────────────────────────
async def create_all_tables() -> None:
    """Create tables if they don't exist (idempotent). Called from app startup."""
    from backend.app import models  # noqa: F401 — registers Detection / AuditEvent
    engine, _ = _init_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def init_models() -> None:
    """
    Create tables on the background DB loop, awaitable from the app's main loop.
    (create_all_tables() must run on the loop that owns the engine.)
    """
    fut = asyncio.run_coroutine_threadsafe(create_all_tables(), _bg())
    await asyncio.wrap_future(fut)


async def get_db():
    """Async FastAPI dependency (provided per spec, for future async routes)."""
    _, sm = _init_engine()
    async with sm() as session:
        yield session


# ── Helpers ─────────────────────────────────────────────────────────────────
def _as_utc(dt: datetime) -> datetime:
    """Attach UTC to a naive datetime; leave aware datetimes unchanged."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _parse_dt(value) -> datetime:
    """Always returns a timezone-aware (UTC) datetime for storage/comparison."""
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, str):
        try:
            return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _to_int(value) -> Optional[int]:
    try:
        return int(round(float(value))) if value is not None else None
    except (TypeError, ValueError):
        return None


# ── High-level async writes (run on the background loop) ────────────────────
async def save_detection(**kw) -> None:
    from backend.app.models.detection_model import Detection
    _, sm = _init_engine()
    async with sm() as s:
        s.add(Detection(
            timestamp=_parse_dt(kw.get("timestamp")),
            source_ip=kw.get("ip"),
            attack_type=kw.get("label"),
            confidence=kw.get("confidence"),
            risk_score=kw.get("risk_score"),
            action_taken=kw.get("action"),
            target_zone=kw.get("target_zone"),
            packets_per_second=kw.get("packets_per_second"),
            avg_request_rate=kw.get("avg_request_rate"),
            failed_connections=_to_int(kw.get("failed_connections")),
            unique_ports=_to_int(kw.get("unique_ports")),
            mitre_tactic=kw.get("mitre_tactic"),
            mitre_technique=kw.get("mitre_technique"),
            sensor_mode=kw.get("sensor_mode") or "demo",
        ))
        await s.commit()


async def save_audit_event(event: dict) -> None:
    from backend.app.models.audit_model import AuditEvent
    _, sm = _init_engine()
    async with sm() as s:
        s.add(AuditEvent(
            timestamp=_parse_dt(event.get("timestamp")),
            event_type=str(event.get("decision") or "event"),
            source_ip=event.get("ip"),
            action=event.get("action"),
            details=event,
        ))
        await s.commit()


async def get_ip_reputation(ip: str) -> Optional[dict]:
    _, sm = _init_engine()
    async with sm() as s:
        row = await s.get(IpReputation, ip)
        if row is None:
            return None
        return {
            "ip": row.ip,
            "abuse_score": row.abuse_score,
            "vt_malicious": row.vt_malicious,
            "is_known_bad": row.is_known_bad,
            "country_code": row.country_code,
            "isp": row.isp,
            "checked_at": _as_utc(row.checked_at).isoformat() if row.checked_at else None,
            "raw_response": row.raw_response,
        }


async def upsert_ip_reputation(**kw) -> None:
    _, sm = _init_engine()
    async with sm() as s:
        row = await s.get(IpReputation, kw["ip"])
        if row is None:
            row = IpReputation(ip=kw["ip"])
            s.add(row)
        row.abuse_score = kw.get("abuse_score")
        row.vt_malicious = kw.get("vt_malicious")
        row.is_known_bad = bool(kw.get("is_known_bad", False))
        row.country_code = kw.get("country_code")
        row.isp = kw.get("isp")
        row.checked_at = kw.get("checked_at") or datetime.now(timezone.utc)
        row.raw_response = kw.get("raw_response")
        await s.commit()


# ── Sync convenience wrappers for the detection pipeline ────────────────────
def save_detection_safe(**kw) -> None:
    """Non-blocking DB write of a detection. Never raises."""
    try:
        run_async_bg(save_detection(**kw))
    except Exception as exc:
        print(f"[DB] detection write skipped: {exc}")


def save_audit_event_safe(event: dict) -> None:
    """Non-blocking DB write of an audit event. Never raises."""
    try:
        run_async_bg(save_audit_event(event))
    except Exception as exc:
        print(f"[DB] audit write skipped: {exc}")


# ── Triage helpers (Phase 3 / Task 1) ───────────────────────────────────────

def _sla_status(case) -> str:
    """Compute SLA status from a TriageCase ORM row."""
    if case.status in ("resolved", "false_positive"):
        return "ok"
    if case.sla_deadline is None:
        return "ok"
    now = datetime.now(timezone.utc)
    deadline = _as_utc(case.sla_deadline)
    if now > deadline:
        return "breached"
    created = _as_utc(case.created_at) if case.created_at else now
    total = (deadline - created).total_seconds()
    elapsed = (now - created).total_seconds()
    if total > 0 and elapsed / total > 0.75:
        return "warning"
    return "ok"


def _triage_to_dict(case, *, include_notes: bool = False) -> dict:
    d = {
        "id": case.id,
        "detection_id": case.detection_id,
        "source_ip": case.source_ip,
        "attack_type": case.attack_type,
        "severity": case.severity,
        "status": case.status,
        "assigned_to": case.assigned_to,
        "created_at":   _as_utc(case.created_at).isoformat()   if case.created_at   else None,
        "updated_at":   _as_utc(case.updated_at).isoformat()   if case.updated_at   else None,
        "resolved_at":  _as_utc(case.resolved_at).isoformat()  if case.resolved_at  else None,
        "sla_deadline": _as_utc(case.sla_deadline).isoformat() if case.sla_deadline else None,
        "sla_status": _sla_status(case),
    }
    if include_notes:
        d["notes"] = case.notes
    return d


async def create_triage_case(**kw) -> dict:
    from backend.app.models.triage_model import TriageCase, risk_to_severity, sla_hours
    _, sm = _init_engine()
    async with sm() as s:
        risk = float(kw.get("risk_score") or 0)
        severity = risk_to_severity(risk)
        now = datetime.now(timezone.utc)
        case = TriageCase(
            detection_id=str(kw.get("detection_id") or ""),
            source_ip=str(kw.get("ip") or ""),
            attack_type=str(kw.get("label") or ""),
            severity=severity,
            status="open",
            created_at=now,
            updated_at=now,
            sla_deadline=now + timedelta(hours=sla_hours(severity)),
        )
        s.add(case)
        await s.commit()
        await s.refresh(case)
        return _triage_to_dict(case)


async def get_triage_cases(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    assigned_to_me: bool = False,
    username: Optional[str] = None,
) -> list:
    from backend.app.models.triage_model import TriageCase
    _, sm = _init_engine()
    async with sm() as s:
        q = sa_select(TriageCase).order_by(TriageCase.created_at.desc())
        if status:
            q = q.where(TriageCase.status == status)
        if severity:
            q = q.where(TriageCase.severity == severity)
        if assigned_to_me and username:
            q = q.where(TriageCase.assigned_to == username)
        result = await s.execute(q)
        return [_triage_to_dict(row) for row in result.scalars().all()]


async def get_triage_case(case_id: str) -> Optional[dict]:
    from backend.app.models.triage_model import TriageCase
    _, sm = _init_engine()
    async with sm() as s:
        case = await s.get(TriageCase, case_id)
        return _triage_to_dict(case, include_notes=True) if case else None


async def update_triage_case(case_id: str, **updates) -> Optional[dict]:
    from backend.app.models.triage_model import TriageCase
    _, sm = _init_engine()
    async with sm() as s:
        case = await s.get(TriageCase, case_id)
        if case is None:
            return None
        for key, value in updates.items():
            if key == "resolved_at" and isinstance(value, str):
                value = _parse_dt(value)
            if hasattr(case, key):
                setattr(case, key, value)
        case.updated_at = datetime.now(timezone.utc)
        await s.commit()
        await s.refresh(case)
        return _triage_to_dict(case, include_notes=True)


async def get_triage_stats() -> dict:
    from backend.app.models.triage_model import TriageCase
    _, sm = _init_engine()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    async with sm() as s:
        result = await s.execute(sa_select(TriageCase))
        all_cases = result.scalars().all()

        total = len(all_cases)
        open_cases = [c for c in all_cases if c.status == "open"]
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for c in open_cases:
            if c.severity in by_severity:
                by_severity[c.severity] += 1

        breached = sum(1 for c in all_cases if _sla_status(c) == "breached")
        with_deadline = [c for c in all_cases if c.sla_deadline]
        sla_breach_rate = round(breached / len(with_deadline), 3) if with_deadline else 0.0

        recent = [c for c in all_cases if c.created_at and _as_utc(c.created_at) >= week_ago]
        resolved_recent = [
            c for c in recent
            if c.status in ("resolved", "false_positive") and c.resolved_at and c.created_at
        ]
        avg_res = None
        if resolved_recent:
            total_mins = sum(
                (_as_utc(c.resolved_at) - _as_utc(c.created_at)).total_seconds() / 60
                for c in resolved_recent
            )
            avg_res = round(total_mins / len(resolved_recent), 1)

        fp = sum(1 for c in recent if c.status == "false_positive")
        fp_rate = round(fp / len(recent), 3) if recent else 0.0
        resolved_total = sum(1 for c in all_cases if c.status in ("resolved", "false_positive"))

        return {
            "by_severity": by_severity,
            "open_count": len(open_cases),
            "total_cases": total,
            "resolved_cases": resolved_total,
            "sla_breach_count": breached,
            "sla_breach_rate": sla_breach_rate,
            "avg_resolution_minutes": avg_res,
            "false_positive_count": fp,
            "false_positive_rate": fp_rate,
        }


def create_triage_case_safe(**kw) -> None:
    """Non-blocking triage case creation. Never raises."""
    try:
        run_async_bg(create_triage_case(**kw))
    except Exception as exc:
        print(f"[TRIAGE] case creation skipped: {exc}")


# ── GeoIP cache helpers (Phase 5A) ───────────────────────────────────────────

async def get_geo_cache(ip: str) -> Optional[dict]:
    _, sm = _init_engine()
    async with sm() as s:
        row = await s.get(GeoIPCache, ip)
        if row is None:
            return None
        return {
            "ip": row.ip,
            "lat": row.lat,
            "lon": row.lon,
            "country_code": row.country_code,
            "country_name": row.country_name,
            "city": row.city,
            "isp": row.isp,
            "source": row.source,
            "cached_at": _as_utc(row.cached_at).isoformat() if row.cached_at else None,
        }


async def upsert_geo_cache(**kw) -> None:
    _, sm = _init_engine()
    async with sm() as s:
        row = await s.get(GeoIPCache, kw["ip"])
        if row is None:
            row = GeoIPCache(ip=kw["ip"])
            s.add(row)
        row.lat          = kw.get("lat")
        row.lon          = kw.get("lon")
        row.country_code = kw.get("country_code")
        row.country_name = kw.get("country_name")
        row.city         = kw.get("city")
        row.isp          = kw.get("isp")
        row.source       = kw.get("source")
        row.cached_at    = kw.get("cached_at") or datetime.now(timezone.utc)
        await s.commit()


async def get_all_geo_cache() -> list:
    _, sm = _init_engine()
    async with sm() as s:
        result = await s.execute(sa_select(GeoIPCache))
        return [
            {
                "ip": r.ip, "lat": r.lat, "lon": r.lon,
                "country_code": r.country_code, "country_name": r.country_name,
                "city": r.city, "isp": r.isp, "source": r.source,
                "cached_at": _as_utc(r.cached_at).isoformat() if r.cached_at else None,
            }
            for r in result.scalars().all()
        ]


# ── Campaign helpers (Phase 5B) ──────────────────────────────────────────────

def _campaign_to_dict(c, *, include_detection_ids: bool = False) -> dict:
    d = {
        "id": c.id,
        "source_ip": c.source_ip,
        "campaign_type": c.campaign_type,
        "stage_count": c.stage_count,
        "attack_types": c.attack_types or [],
        "started_at":   _as_utc(c.started_at).isoformat()   if c.started_at   else None,
        "last_seen_at": _as_utc(c.last_seen_at).isoformat() if c.last_seen_at else None,
        "ended_at":     _as_utc(c.ended_at).isoformat()     if c.ended_at     else None,
        "status": c.status,
        "severity": c.severity,
        "total_detections": c.total_detections,
        "mitre_stages": c.mitre_stages or [],
        "geo_country": c.geo_country,
    }
    if include_detection_ids:
        d["detection_ids"] = c.detection_ids or []
    return d


async def create_campaign(**kw) -> dict:
    from backend.app.models.campaign_model import Campaign
    _, sm = _init_engine()
    now = datetime.now(timezone.utc)
    async with sm() as s:
        c = Campaign(
            id=kw.get("id") or str(uuid.uuid4()),
            source_ip=kw.get("source_ip"),
            campaign_type=kw.get("campaign_type"),
            stage_count=int(kw.get("stage_count") or 0),
            attack_types=kw.get("attack_types") or [],
            detection_ids=kw.get("detection_ids") or [],
            started_at=_parse_dt(kw.get("started_at")) if kw.get("started_at") else now,
            last_seen_at=_parse_dt(kw.get("last_seen_at")) if kw.get("last_seen_at") else now,
            status=kw.get("status") or "active",
            severity=kw.get("severity") or "medium",
            total_detections=int(kw.get("total_detections") or 0),
            mitre_stages=kw.get("mitre_stages") or [],
            geo_country=kw.get("geo_country"),
        )
        s.add(c)
        await s.commit()
        await s.refresh(c)
        return _campaign_to_dict(c)


async def update_campaign(campaign_id: str, **updates) -> Optional[dict]:
    from backend.app.models.campaign_model import Campaign
    _, sm = _init_engine()
    async with sm() as s:
        c = await s.get(Campaign, campaign_id)
        if c is None:
            return None
        for key, value in updates.items():
            if key in ("started_at", "last_seen_at", "ended_at") and isinstance(value, str):
                value = _parse_dt(value)
            if hasattr(c, key):
                setattr(c, key, value)
        await s.commit()
        await s.refresh(c)
        return _campaign_to_dict(c)


async def get_campaigns(status: Optional[str] = None, limit: int = 50) -> list:
    from backend.app.models.campaign_model import Campaign
    _, sm = _init_engine()
    async with sm() as s:
        q = sa_select(Campaign).order_by(Campaign.started_at.desc())
        if status:
            q = q.where(Campaign.status == status)
        q = q.limit(limit)
        result = await s.execute(q)
        return [_campaign_to_dict(c) for c in result.scalars().all()]


async def get_campaign(campaign_id: str) -> Optional[dict]:
    from backend.app.models.campaign_model import Campaign
    _, sm = _init_engine()
    async with sm() as s:
        c = await s.get(Campaign, campaign_id)
        return _campaign_to_dict(c, include_detection_ids=True) if c else None


async def get_active_campaigns() -> list:
    return await get_campaigns(status="active", limit=200)


async def get_active_campaign_by_ip(ip: str) -> Optional[dict]:
    from backend.app.models.campaign_model import Campaign
    _, sm = _init_engine()
    async with sm() as s:
        q = (
            sa_select(Campaign)
            .where(Campaign.source_ip == ip, Campaign.status == "active")
            .order_by(Campaign.started_at.desc())
            .limit(1)
        )
        result = await s.execute(q)
        c = result.scalars().first()
        return _campaign_to_dict(c) if c else None


async def get_campaign_stats() -> dict:
    from backend.app.models.campaign_model import Campaign
    _, sm = _init_engine()
    async with sm() as s:
        result = await s.execute(sa_select(Campaign))
        all_c = result.scalars().all()

        total = len(all_c)
        active = sum(1 for c in all_c if c.status == "active")
        completed = total - active

        # avg duration (minutes) over completed campaigns with an ended_at
        durations = []
        for c in all_c:
            if c.ended_at and c.started_at:
                durations.append((_as_utc(c.ended_at) - _as_utc(c.started_at)).total_seconds() / 60)
        avg_duration = round(sum(durations) / len(durations), 1) if durations else None

        # top attacker + most common type
        ip_counts: dict = {}
        type_counts: dict = {}
        for c in all_c:
            ip_counts[c.source_ip] = ip_counts.get(c.source_ip, 0) + 1
            type_counts[c.campaign_type] = type_counts.get(c.campaign_type, 0) + 1
        top_ip = max(ip_counts, key=ip_counts.get) if ip_counts else None
        top_type = max(type_counts, key=type_counts.get) if type_counts else None

        return {
            "total_campaigns": total,
            "active_campaigns": active,
            "completed_campaigns": completed,
            "avg_duration_minutes": avg_duration,
            "top_attacker_ip": top_ip,
            "most_common_type": top_type,
        }


# ── CVE helpers (Phase 5C) ───────────────────────────────────────────────────

def _cve_to_dict(c) -> dict:
    return {
        "cve_id": c.cve_id,
        "vendor_project": c.vendor_project,
        "product": c.product,
        "vulnerability_name": c.vulnerability_name,
        "date_added": c.date_added.isoformat() if c.date_added else None,
        "short_description": c.short_description,
        "required_action": c.required_action,
        "due_date": c.due_date.isoformat() if c.due_date else None,
        "known_ransomware": bool(c.known_ransomware),
        "search_text": c.search_text,
    }


async def upsert_cves(cve_list: list) -> int:
    """Bulk upsert CVE entries. Each item is a dict with the KEV fields."""
    from backend.app.models.cve_model import CVEEntry
    from datetime import date as _date
    _, sm = _init_engine()

    def _parse_date(v):
        if not v:
            return None
        try:
            return _date.fromisoformat(str(v)[:10])
        except Exception:
            return None

    count = 0
    async with sm() as s:
        for item in cve_list:
            cid = item.get("cve_id")
            if not cid:
                continue
            row = await s.get(CVEEntry, cid)
            if row is None:
                row = CVEEntry(cve_id=cid)
                s.add(row)
            row.vendor_project     = item.get("vendor_project")
            row.product            = item.get("product")
            row.vulnerability_name = item.get("vulnerability_name")
            row.date_added         = _parse_date(item.get("date_added"))
            row.short_description  = item.get("short_description")
            row.required_action    = item.get("required_action")
            row.due_date           = _parse_date(item.get("due_date"))
            row.known_ransomware   = bool(item.get("known_ransomware"))
            row.search_text        = item.get("search_text")
            row.updated_at         = datetime.now(timezone.utc)
            count += 1
        await s.commit()
    return count


async def get_all_cves() -> list:
    from backend.app.models.cve_model import CVEEntry
    _, sm = _init_engine()
    async with sm() as s:
        result = await s.execute(sa_select(CVEEntry))
        return [_cve_to_dict(c) for c in result.scalars().all()]


async def get_cve(cve_id: str) -> Optional[dict]:
    from backend.app.models.cve_model import CVEEntry
    _, sm = _init_engine()
    async with sm() as s:
        c = await s.get(CVEEntry, cve_id)
        return _cve_to_dict(c) if c else None


async def get_recent_cves(days: int = 30) -> list:
    from backend.app.models.cve_model import CVEEntry
    from datetime import date as _date, timedelta as _td
    _, sm = _init_engine()
    cutoff = _date.today() - _td(days=days)
    async with sm() as s:
        q = (
            sa_select(CVEEntry)
            .where(CVEEntry.date_added >= cutoff)
            .order_by(CVEEntry.date_added.desc())
        )
        result = await s.execute(q)
        return [_cve_to_dict(c) for c in result.scalars().all()]


async def link_cve_to_detection(detection_id: str, cve_id: str, relevance: float) -> None:
    from backend.app.models.cve_model import CVEDetection
    _, sm = _init_engine()
    async with sm() as s:
        s.add(CVEDetection(
            detection_id=detection_id,
            cve_id=cve_id,
            relevance_score=float(relevance) if relevance is not None else None,
            matched_at=datetime.now(timezone.utc),
        ))
        await s.commit()


async def get_cve_stats() -> dict:
    from backend.app.models.cve_model import CVEEntry
    from datetime import date as _date, timedelta as _td
    _, sm = _init_engine()
    cutoff = _date.today() - _td(days=30)
    async with sm() as s:
        result = await s.execute(sa_select(CVEEntry))
        all_c = result.scalars().all()

        total = len(all_c)
        ransomware = sum(1 for c in all_c if c.known_ransomware)
        recent = sum(1 for c in all_c if c.date_added and c.date_added >= cutoff)
        last_updated = max((c.updated_at for c in all_c if c.updated_at), default=None)

        vendor_counts: dict = {}
        for c in all_c:
            v = c.vendor_project or "Unknown"
            vendor_counts[v] = vendor_counts.get(v, 0) + 1
        top_vendors = [
            {"vendor": v, "count": n}
            for v, n in sorted(vendor_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
        ]

        return {
            "total_cves": total,
            "last_updated": _as_utc(last_updated).isoformat() if last_updated else None,
            "ransomware_count": ransomware,
            "recent_30_days": recent,
            "top_vendors": top_vendors,
        }


async def complete_stale_campaigns(max_idle_seconds: int = 1800) -> list:
    """Mark active campaigns idle for > max_idle_seconds as completed.
    Returns the list of campaigns that were just completed."""
    from backend.app.models.campaign_model import Campaign
    _, sm = _init_engine()
    now = datetime.now(timezone.utc)
    completed = []
    async with sm() as s:
        q = sa_select(Campaign).where(Campaign.status == "active")
        result = await s.execute(q)
        for c in result.scalars().all():
            last = _as_utc(c.last_seen_at) if c.last_seen_at else None
            if last and (now - last).total_seconds() > max_idle_seconds:
                c.status = "completed"
                c.ended_at = now
                completed.append(_campaign_to_dict(c))
        if completed:
            await s.commit()
    return completed
