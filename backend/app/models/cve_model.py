"""CVE ORM models — Phase 5C.

cve_entries mirrors the CISA Known Exploited Vulnerabilities (KEV) catalog.
cve_detections links a detection (CSV-based, so detection_id is a plain string,
not a FK) to a matched CVE with a relevance score.
"""
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class CVEEntry(Base):
    __tablename__ = "cve_entries"

    cve_id:              Mapped[str]              = mapped_column(String(30), primary_key=True)
    vendor_project:      Mapped[Optional[str]]    = mapped_column(String(200), nullable=True)
    product:             Mapped[Optional[str]]    = mapped_column(String(200), nullable=True)
    vulnerability_name:  Mapped[Optional[str]]    = mapped_column(String(500), nullable=True)
    date_added:          Mapped[Optional[date]]   = mapped_column(Date, nullable=True, index=True)
    short_description:   Mapped[Optional[str]]    = mapped_column(Text, nullable=True)
    required_action:     Mapped[Optional[str]]    = mapped_column(Text, nullable=True)
    due_date:            Mapped[Optional[date]]   = mapped_column(Date, nullable=True)
    known_ransomware:    Mapped[bool]             = mapped_column(Boolean, default=False)
    search_text:         Mapped[Optional[str]]    = mapped_column(Text, nullable=True)
    created_at:          Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:          Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CVEDetection(Base):
    __tablename__ = "cve_detections"

    id:              Mapped[str]              = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    detection_id:    Mapped[str]              = mapped_column(String(100), index=True)
    cve_id:          Mapped[str]              = mapped_column(String(30), index=True)
    relevance_score: Mapped[Optional[float]]  = mapped_column(Float, nullable=True)
    matched_at:      Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now())
