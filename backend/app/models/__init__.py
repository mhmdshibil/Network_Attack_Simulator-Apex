"""SQLAlchemy models package. Importing it registers all tables on Base.metadata."""
from backend.app.models.detection_model import Detection
from backend.app.models.audit_model import AuditEvent
from backend.app.core.database import IpReputation

__all__ = ["Detection", "AuditEvent", "IpReputation"]
