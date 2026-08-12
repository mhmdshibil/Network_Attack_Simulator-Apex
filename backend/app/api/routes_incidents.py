"""LLM incident summary endpoint — Phase 10."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.services.llm_summary import generate_summary, get_cached
from backend.app.ml.mitre_mapping import get_mitre
from backend.app.ml.shap_explainer import load_explanation
from backend.app.core.auth import require_analyst

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


class SummarizeRequest(BaseModel):
    ip: str
    timestamp: str
    label: str
    confidence: float = 0.0
    risk_score: float = 0.0
    action: str = "monitored"


@router.post("/summarize")
def summarize(req: SummarizeRequest, _: dict = Depends(require_analyst)):
    """
    Generate (or return cached) a 2-3 sentence LLM incident summary
    plus recommended action for a specific detection.
    """
    detection = req.model_dump()
    detection["mitre"] = get_mitre(req.label)

    # Enrich with SHAP if available
    shap = load_explanation(req.ip, req.timestamp)
    detection["shap_top3"] = shap["shap_top3"] if shap else []

    return generate_summary(detection)


@router.get("/summary")
def get_summary(ip: str, ts: str, _: dict = Depends(require_analyst)):
    """Return a previously cached summary without regenerating."""
    cached = get_cached(ip, ts)
    if cached is None:
        raise HTTPException(status_code=404, detail="No cached summary for this detection")
    return {**cached, "cached": True}
