"""Alert Correlation Rules Engine ORM model — Phase 6A."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class Rule(Base):
    __tablename__ = "rules"

    id:            Mapped[str]              = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name:          Mapped[str]              = mapped_column(String(100), nullable=False)
    description:   Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    enabled:       Mapped[bool]            = mapped_column(Boolean, default=True, nullable=False)
    conditions:    Mapped[list]            = mapped_column(JSON, default=list, nullable=False)
    action:        Mapped[str]             = mapped_column(String(20), nullable=False)
    priority:      Mapped[int]             = mapped_column(Integer, default=10, nullable=False)
    created_by:    Mapped[str]             = mapped_column(String(50), default="system", nullable=False)
    created_at:    Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    trigger_count: Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    last_triggered: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
