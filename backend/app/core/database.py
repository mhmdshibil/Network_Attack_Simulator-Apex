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
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, func
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
