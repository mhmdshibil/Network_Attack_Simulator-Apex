"""Detection ORM model — mirrors detections.csv (ip, timestamp, label, action,
risk_score) plus the feature vector, MITRE enrichment and sensor metadata."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class Detection(Base):
    __tablename__ = "detections"

    id:                 Mapped[str]              = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp:          Mapped[datetime]         = mapped_column(DateTime(timezone=True), index=True)
    source_ip:          Mapped[str]              = mapped_column(String(45), index=True)
    attack_type:        Mapped[str]              = mapped_column(String(50), index=True)
    confidence:         Mapped[Optional[float]]  = mapped_column(Float, nullable=True)
    risk_score:         Mapped[Optional[float]]  = mapped_column(Float, nullable=True)
    action_taken:       Mapped[Optional[str]]    = mapped_column(String(20), nullable=True)
    target_zone:        Mapped[Optional[str]]    = mapped_column(String(20), nullable=True)
    packets_per_second: Mapped[Optional[float]]  = mapped_column(Float, nullable=True)
    avg_request_rate:   Mapped[Optional[float]]  = mapped_column(Float, nullable=True)
    failed_connections: Mapped[Optional[int]]    = mapped_column(Integer, nullable=True)
    unique_ports:       Mapped[Optional[int]]    = mapped_column(Integer, nullable=True)
    mitre_tactic:       Mapped[Optional[str]]    = mapped_column(String(100), nullable=True)
    mitre_technique:    Mapped[Optional[str]]    = mapped_column(String(100), nullable=True)
    sensor_mode:        Mapped[str]              = mapped_column(String(10), default="demo")
    created_at:         Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now())
