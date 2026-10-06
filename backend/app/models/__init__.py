"""SQLAlchemy models package. Importing it registers all tables on Base.metadata."""
from backend.app.models.detection_model import Detection
from backend.app.models.audit_model import AuditEvent
from backend.app.models.triage_model import TriageCase
from backend.app.models.campaign_model import Campaign
from backend.app.models.cve_model import CVEEntry, CVEDetection
from backend.app.models.rules_model import Rule
from backend.app.models.webhook_model import Webhook, WebhookDelivery
from backend.app.models.push_model import PushSubscription
from backend.app.core.database import IpReputation, GeoIPCache

__all__ = [
    "Detection", "AuditEvent", "TriageCase", "Campaign",
    "CVEEntry", "CVEDetection", "Rule", "Webhook", "WebhookDelivery",
    "PushSubscription", "IpReputation", "GeoIPCache",
]
