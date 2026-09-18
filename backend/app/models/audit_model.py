"""AuditEvent ORM model — mirrors security_events.jsonl. The full event dict is
stored in the JSON `details` column; key fields are also extracted for querying."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id:         Mapped[str]              = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp:  Mapped[datetime]         = mapped_column(DateTime(timezone=True), index=True)
    event_type: Mapped[Optional[str]]    = mapped_column(String(50), nullable=True)
    source_ip:  Mapped[Optional[str]]    = mapped_column(String(45), nullable=True)
    action:     Mapped[Optional[str]]    = mapped_column(String(20), nullable=True)
    details:    Mapped[Optional[dict]]   = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now())
