# backend/app/schemas/metrics.py
# This file is intended to hold Pydantic schemas related to system and performance metrics.
# By defining data models here, the application can ensure that the data structures used for
# metrics are consistent, validated, and well-documented. These schemas are particularly useful
# for serializing data to be sent over the network via API endpoints, ensuring that clients
# receive data in a predictable and reliable format.
#
# Example Usage:
#
# from pydantic import BaseModel
# from typing import Dict, Optional
# from datetime import datetime
#
# class SystemMetrics(BaseModel):
#     total_detections: int
#     unique_blocked_ips: int
#     by_label: Dict[str, int]
#     last_detection: Optional[datetime]
#
