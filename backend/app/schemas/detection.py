# backend/app/schemas/detection.py
# This file is intended to hold Pydantic schemas related to attack detections. Schemas define the
# structure, data types, and validation rules for the data that the application works with. By using
# Pydantic models, the application can ensure data integrity and provide clear, machine-readable
# documentation for API endpoints.
#
# For example, a schema for a single detection event could be defined here to ensure that every
# detection record contains the necessary fields, such as an IP address, a timestamp, and a label.
#
# Example Usage:
#
# from pydantic import BaseModel
# from datetime import datetime
#
# class Detection(BaseModel):
#     ip: str
#     timestamp: datetime
#     label: str
#     action: str
#
from typing import Optional

from pydantic import BaseModel


class FeatureWindowIn(BaseModel):
    """
    A single aggregated feature window POSTed to /api/detections by a sensor
    (see sensor_agent.py). The four feature fields are required and numeric —
    FastAPI returns 422 automatically if any is missing or non-numeric.
    """
    source_ip: str
    packets_per_second: float
    avg_request_rate: float
    failed_connections: float
    unique_ports: float
    target_zone: Optional[str] = None   # optional — carried through to the WS broadcast
    window_start: Optional[str] = None  # optional ISO timestamp of the window
    sensor_mode: Optional[str] = None   # optional — "demo" | "real"


class IngestResult(BaseModel):
    """Response for a processed feature window."""
    status: str
    detection_id: str
    label: str
    action: str
    target_zone: Optional[str] = None

