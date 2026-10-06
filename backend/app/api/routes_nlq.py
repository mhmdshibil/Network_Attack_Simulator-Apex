"""
Natural Language Query API — Phase 6D.

POST /api/nlq
  Auth: analyst+
  Body: {query: "show bruteforce attacks from Russia last week"}

Steps:
1. Send query + schema to Claude Haiku (graceful no-op without API key)
2. Parse JSON filters from Claude's response
3. Apply filters to the detections CSV / DB
4. Return matching detections (max 100) + meta

Graceful degradation:
- No ANTHROPIC_API_KEY → {error: "NLQ requires ANTHROPIC_API_KEY in .env"}
- Claude timeout / bad JSON → {error: "...", raw: "..."}
- No DB / CSV fallback → read from CSV directly
"""
import asyncio
import csv
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import require_analyst
from backend.app.core.paths import DETECTIONS_FILE

router = APIRouter(prefix="/api/nlq", tags=["nlq"])

_SYSTEM_PROMPT = """You are a query parser for a network security system.
Convert natural language queries to JSON filter objects.
Available fields:
  attack_type (values: port_scan, ddos, bruteforce, sql_injection, malware, unknown_anomaly)
  country_code (ISO 2-letter, e.g. "DE", "RU")
  risk_score (0-100, integer)
  confidence (0.0-1.0, float)
  action_taken (block, rate_limit, monitor, allow)
  start_time (ISO datetime string)
  end_time (ISO datetime string)
  source_ip (string)
Return ONLY valid JSON with any matching fields, no explanation, no markdown.
If a relative time is mentioned (e.g. "last week"), compute from today's UTC date.
Example: {"attack_type": "bruteforce", "country_code": "DE", "start_time": "2026-09-28T00:00:00Z"}"""


async def _parse_query_with_claude(query: str) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return {"_error": "NLQ requires ANTHROPIC_API_KEY in .env"}

    try:
        import anthropic
    except ImportError:
        return {"_error": "anthropic package not installed"}

    client = anthropic.Anthropic(api_key=api_key)
    try:
        msg = await asyncio.wait_for(
            asyncio.to_thread(
                client.messages.create,
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": query}],
            ),
            timeout=10,
        )
        raw = msg.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        return {"_ok": True, "_raw": raw, **json.loads(raw)}
    except asyncio.TimeoutError:
        return {"_error": "Claude API timeout (>10s)"}
    except json.JSONDecodeError as e:
        return {"_error": f"Could not parse Claude response: {e}", "_raw": raw if 'raw' in dir() else ""}
    except Exception as e:
        return {"_error": str(e)}


def _apply_filters(filters: dict, limit: int = 100) -> tuple[list[dict], int]:
    """Apply filter dict to detections. Returns (rows, total_matched)."""
    rows = []

    # Time range helpers
    start_dt = None
    end_dt   = None
    if filters.get("start_time"):
        try:
            start_dt = datetime.fromisoformat(filters["start_time"].replace("Z", "+00:00"))
        except Exception:
            pass
    if filters.get("end_time"):
        try:
            end_dt = datetime.fromisoformat(filters["end_time"].replace("Z", "+00:00"))
        except Exception:
            pass

    # Try DB first
    try:
        from backend.app.core.database import run_async
        import sqlalchemy as sa
        from backend.app.models.detection_model import Detection
        from backend.app.core.database import _init_engine

        async def _db_query():
            _, sm = _init_engine()
            async with sm() as s:
                q = sa.select(Detection).order_by(Detection.timestamp.desc()).limit(500)
                result = await s.execute(q)
                return result.scalars().all()

        detections = run_async(_db_query(), timeout=10)
        for d in detections:
            row = {
                "ip": d.source_ip, "timestamp": d.timestamp.isoformat() if d.timestamp else None,
                "label": d.attack_type, "action": d.action_taken,
                "risk_score": d.risk_score, "confidence": d.confidence,
            }
            if _row_matches(row, filters, start_dt, end_dt):
                rows.append(row)
        return rows[:limit], len(rows)
    except Exception:
        pass

    # CSV fallback
    if DETECTIONS_FILE.exists():
        try:
            with open(DETECTIONS_FILE) as f:
                for raw in csv.DictReader(f):
                    row = {
                        "ip": raw.get("ip"), "timestamp": raw.get("timestamp"),
                        "label": raw.get("label"), "action": raw.get("action"),
                        "risk_score": _safe_float(raw.get("risk_score")),
                        "confidence": None,
                    }
                    if _row_matches(row, filters, start_dt, end_dt):
                        rows.append(row)
            rows.reverse()
            return rows[:limit], len(rows)
        except Exception:
            pass

    return [], 0


def _safe_float(v):
    try: return float(v)
    except Exception: return None


def _row_matches(row: dict, filters: dict, start_dt, end_dt) -> bool:
    if filters.get("attack_type") and row.get("label") != filters["attack_type"]:
        return False
    if filters.get("source_ip") and row.get("ip") != filters["source_ip"]:
        return False
    if filters.get("action_taken") and row.get("action") != filters["action_taken"]:
        return False
    if filters.get("risk_score") is not None:
        score = row.get("risk_score")
        if score is None or float(score) < float(filters["risk_score"]):
            return False
    if filters.get("confidence") is not None:
        conf = row.get("confidence")
        if conf is None or float(conf) < float(filters["confidence"]):
            return False
    if start_dt or end_dt:
        ts = row.get("timestamp")
        if ts:
            try:
                row_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                if row_dt.tzinfo is None:
                    row_dt = row_dt.replace(tzinfo=timezone.utc)
                if start_dt and row_dt < start_dt: return False
                if end_dt   and row_dt > end_dt:   return False
            except Exception:
                pass
    # country_code filter requires geo data — skip if not in row
    if filters.get("country_code"):
        geo_cc = row.get("country_code") or (row.get("geo") or {}).get("country_code")
        if geo_cc and geo_cc != filters["country_code"]:
            return False
    return True


@router.post("")
async def nlq_query(body: dict, _: dict = Depends(require_analyst)):
    query = (body.get("query") or "").strip()
    if not query:
        raise HTTPException(422, "query is required")

    t0 = time.monotonic()

    # Check API key before calling Claude
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        return {
            "error": "NLQ requires ANTHROPIC_API_KEY in .env",
            "parsed_filters": {},
            "results": [],
            "result_count": 0,
            "query_time_ms": 0,
        }

    parsed = await _parse_query_with_claude(query)

    if parsed.get("_error"):
        return {
            "error": parsed["_error"],
            "raw": parsed.get("_raw"),
            "parsed_filters": {},
            "results": [],
            "result_count": 0,
            "query_time_ms": round((time.monotonic() - t0) * 1000),
        }

    # Clean internal keys before passing to filter
    clean_filters = {k: v for k, v in parsed.items() if not k.startswith("_")}

    results, total = _apply_filters(clean_filters)
    return {
        "parsed_filters": clean_filters,
        "results": results,
        "result_count": total,
        "query_time_ms": round((time.monotonic() - t0) * 1000),
    }
