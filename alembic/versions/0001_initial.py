"""initial schema — detections, audit_events, ip_reputation

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-18
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "detections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_ip", sa.String(length=45), nullable=False),
        sa.Column("attack_type", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("action_taken", sa.String(length=20), nullable=True),
        sa.Column("target_zone", sa.String(length=20), nullable=True),
        sa.Column("packets_per_second", sa.Float(), nullable=True),
        sa.Column("avg_request_rate", sa.Float(), nullable=True),
        sa.Column("failed_connections", sa.Integer(), nullable=True),
        sa.Column("unique_ports", sa.Integer(), nullable=True),
        sa.Column("mitre_tactic", sa.String(length=100), nullable=True),
        sa.Column("mitre_technique", sa.String(length=100), nullable=True),
        sa.Column("sensor_mode", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_detections_timestamp", "detections", ["timestamp"])
    op.create_index("ix_detections_source_ip", "detections", ["source_ip"])
    op.create_index("ix_detections_attack_type", "detections", ["attack_type"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=True),
        sa.Column("source_ip", sa.String(length=45), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"])

    op.create_table(
        "ip_reputation",
        sa.Column("ip", sa.String(length=45), primary_key=True),
        sa.Column("abuse_score", sa.Integer(), nullable=True),
        sa.Column("vt_malicious", sa.Integer(), nullable=True),
        sa.Column("is_known_bad", sa.Boolean(), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("isp", sa.String(length=200), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ip_reputation")
    op.drop_index("ix_audit_events_timestamp", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_detections_attack_type", table_name="detections")
    op.drop_index("ix_detections_source_ip", table_name="detections")
    op.drop_index("ix_detections_timestamp", table_name="detections")
    op.drop_table("detections")
