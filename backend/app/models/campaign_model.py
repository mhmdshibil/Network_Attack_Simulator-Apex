"""Campaign ORM model — Phase 5B.

A Campaign groups multiple detections from the same source_ip into a single
coordinated multi-stage attack entity. Created by campaign_service when any
correlation rule fires (multi_vector / kill_chain / high_volume).
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id:               Mapped[str]              = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_ip:        Mapped[str]              = mapped_column(String(45), index=True)
    campaign_type:    Mapped[str]              = mapped_column(String(50))   # multi_vector | kill_chain | high_volume
    stage_count:      Mapped[int]              = mapped_column(Integer, default=0)
    attack_types:     Mapped[Optional[list]]   = mapped_column(JSON, nullable=True)
    detection_ids:    Mapped[Optional[list]]   = mapped_column(JSON, nullable=True)
    started_at:       Mapped[datetime]         = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at:     Mapped[datetime]         = mapped_column(DateTime(timezone=True))
    ended_at:         Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status:           Mapped[str]              = mapped_column(String(20), default="active", index=True)  # active | completed
    severity:         Mapped[str]              = mapped_column(String(10), default="medium")  # high | medium
    total_detections: Mapped[int]              = mapped_column(Integer, default=0)
    mitre_stages:     Mapped[Optional[list]]   = mapped_column(JSON, nullable=True)
    geo_country:      Mapped[Optional[str]]    = mapped_column(String(100), nullable=True)
    created_at:       Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now())
