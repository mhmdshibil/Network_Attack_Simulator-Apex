"""Webhook ORM models — Phase 6C."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class Webhook(Base):
    __tablename__ = "webhooks"

    id:               Mapped[str]              = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name:             Mapped[str]              = mapped_column(String(100), nullable=False)
    url:              Mapped[str]              = mapped_column(String(500), nullable=False)
    events:           Mapped[list]             = mapped_column(JSON, default=list, nullable=False)
    secret:           Mapped[Optional[str]]    = mapped_column(String(100), nullable=True)
    enabled:          Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    created_at:       Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_triggered:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_deliveries: Mapped[int]              = mapped_column(Integer, default=0, nullable=False)
    failed_deliveries: Mapped[int]             = mapped_column(Integer, default=0, nullable=False)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id:            Mapped[str]              = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    webhook_id:    Mapped[str]              = mapped_column(String(36), index=True, nullable=False)
    event_type:    Mapped[str]              = mapped_column(String(50), nullable=False)
    status:        Mapped[str]              = mapped_column(String(20), nullable=False)  # success|failed|timeout
    response_code: Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    attempt:       Mapped[int]             = mapped_column(Integer, default=1, nullable=False)
    delivered_at:  Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
