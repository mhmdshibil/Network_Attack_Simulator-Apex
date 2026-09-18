"""TriageCase ORM model — Phase 3 / Task 1.

Alert triage lifecycle: open → acknowledged → investigating → resolved | false_positive.
SLA deadlines are set at creation time based on severity derived from risk_score.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


def risk_to_severity(risk_score: float) -> str:
    """Map ML risk score (0–100) to triage severity tier."""
    if risk_score > 85:
        return "critical"
    if risk_score >= 60:
        return "high"
    if risk_score >= 30:
        return "medium"
    return "low"


def sla_hours(severity: str) -> int:
    """Resolution SLA window in hours per severity tier."""
    return {"critical": 4, "high": 8, "medium": 24, "low": 72}.get(severity, 24)


class TriageCase(Base):
    __tablename__ = "triage_cases"

    id:           Mapped[str]              = mapped_column(String(36), primary_key=True,
                                                           default=lambda: str(uuid.uuid4()))
    detection_id: Mapped[str]              = mapped_column(String(100), index=True)
    source_ip:    Mapped[str]              = mapped_column(String(45))
    attack_type:  Mapped[str]              = mapped_column(String(50))
    severity:     Mapped[str]              = mapped_column(String(10), default="low")
    status:       Mapped[str]              = mapped_column(String(20), default="open")
    assigned_to:  Mapped[Optional[str]]    = mapped_column(String(50), nullable=True)
    notes:        Mapped[Optional[str]]    = mapped_column(Text, nullable=True)
    created_at:   Mapped[datetime]         = mapped_column(DateTime(timezone=True),
                                                           default=lambda: datetime.now(timezone.utc))
    updated_at:   Mapped[datetime]         = mapped_column(DateTime(timezone=True),
                                                           default=lambda: datetime.now(timezone.utc))
    resolved_at:  Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
