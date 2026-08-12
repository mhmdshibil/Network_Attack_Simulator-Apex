"""SHAP explainability endpoint — Phase 5."""
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.ml.shap_explainer import load_explanation
from backend.app.core.auth import require_analyst

router = APIRouter(prefix="/api/explain", tags=["explainability"])


@router.get("/")
def explain(ip: str = Query(...), ts: str | None = Query(None), _: dict = Depends(require_analyst)):
    """
    Return the SHAP explanation for the most recent detection from an IP.
    Optionally filter by exact timestamp (ts).
    """
    record = load_explanation(ip, timestamp=ts)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No SHAP explanation found for IP {ip}"
        )
    return record
