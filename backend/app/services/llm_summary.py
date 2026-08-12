"""
LLM-generated incident summaries — Phase 10.

Calls Claude claude-haiku-4-5-20251001 with detection context and returns a 2-3 sentence
analyst note + recommended action. Results are cached in
data/processed/incident_summaries.jsonl so the API is not called again
on dashboard refresh.

Requires ANTHROPIC_API_KEY in the environment (or .env file).
If the key is absent the endpoint returns a graceful fallback.
"""
import json
import os
from pathlib import Path

from backend.app.core.paths import PROCESSED_DIR

_SUMMARIES_FILE = PROCESSED_DIR / "incident_summaries.jsonl"
_CACHE: dict[str, dict] = {}   # in-memory mirror so hot lookups skip disk I/O
_CACHE_LOADED = False


def _load_cache():
    global _CACHE_LOADED
    if _CACHE_LOADED or not _SUMMARIES_FILE.exists():
        _CACHE_LOADED = True
        return
    with _SUMMARIES_FILE.open() as f:
        for line in f:
            try:
                rec = json.loads(line)
                _CACHE[_cache_key(rec["ip"], rec["timestamp"])] = rec
            except Exception:
                pass
    _CACHE_LOADED = True


def _cache_key(ip: str, timestamp: str) -> str:
    return f"{ip}::{timestamp}"


def _store(record: dict):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with _SUMMARIES_FILE.open("a") as f:
        f.write(json.dumps(record) + "\n")
    _CACHE[_cache_key(record["ip"], record["timestamp"])] = record


def get_cached(ip: str, timestamp: str) -> dict | None:
    _load_cache()
    return _CACHE.get(_cache_key(ip, timestamp))


def _build_prompt(detection: dict) -> str:
    label = detection.get("label", "unknown")
    ip = detection.get("ip", "unknown")
    risk = detection.get("risk_score", 0)
    conf = detection.get("confidence", 0)
    mitre = detection.get("mitre", {})
    shap = detection.get("shap_top3", [])
    action = detection.get("action", "unknown")

    shap_lines = "\n".join(
        f"  - {s['feature'].replace('_',' ')}: value={s['value']}, SHAP={s['shap']:+.3f} ({s['direction']})"
        for s in shap
    ) or "  - No SHAP data available"

    return f"""You are a senior SOC analyst writing a terse incident note for a security dashboard.

Detection context:
- Attack type: {label.replace('_',' ')}
- Source IP: {ip}
- Risk score: {risk}/100
- Confidence: {conf:.0%}
- Automated action taken: {action}
- MITRE ATT&CK: {mitre.get('technique_id','?')} – {mitre.get('technique','?')} ({mitre.get('tactic','?')})
- Top contributing features (SHAP):
{shap_lines}

Write exactly two parts, clearly labelled:
1. SUMMARY: A 2–3 sentence factual description of what happened, referencing the specific attack type, IP, risk level, and top features.
2. RECOMMENDATION: One sentence recommending the immediate next action for the analyst.

Be concrete and specific. Do not use generic filler phrases."""


def generate_summary(detection: dict) -> dict:
    """
    Return a cached or freshly generated incident summary dict:
      { ip, timestamp, summary, recommendation, cached }
    """
    ip = detection.get("ip", "")
    timestamp = detection.get("timestamp", "")

    cached = get_cached(ip, timestamp)
    if cached:
        return {**cached, "cached": True}

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {
            "ip": ip,
            "timestamp": timestamp,
            "summary": "LLM summaries require ANTHROPIC_API_KEY in the environment.",
            "recommendation": "Set ANTHROPIC_API_KEY and retry.",
            "cached": False,
            "error": "no_api_key",
        }

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": _build_prompt(detection)}],
        )
        raw = message.content[0].text.strip()

        # Parse the two labelled sections
        summary = ""
        recommendation = ""
        for line in raw.splitlines():
            if line.upper().startswith("SUMMARY:"):
                summary = line[len("SUMMARY:"):].strip()
            elif line.upper().startswith("RECOMMENDATION:"):
                recommendation = line[len("RECOMMENDATION:"):].strip()
            elif summary and not recommendation:
                summary += " " + line.strip()

        if not summary:
            summary = raw
        if not recommendation:
            recommendation = "Review detection manually."

        record = {
            "ip": ip,
            "timestamp": timestamp,
            "summary": summary,
            "recommendation": recommendation,
            "cached": False,
        }
        _store(record)
        return record

    except Exception as exc:
        return {
            "ip": ip,
            "timestamp": timestamp,
            "summary": f"Summary generation failed: {exc}",
            "recommendation": "Check API key and network connectivity.",
            "cached": False,
            "error": str(exc),
        }
