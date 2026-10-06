"""Push subscription ORM model — Phase 6E."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id:         Mapped[str]              = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    endpoint:   Mapped[str]             = mapped_column(Text, nullable=False, unique=True)
    p256dh:     Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    auth:       Mapped[Optional[str]]   = mapped_column(Text, nullable=True)
    user_agent: Mapped[Optional[str]]   = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used:  Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
