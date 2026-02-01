# backend/app/schemas/traffic.py
# This file is intended to hold Pydantic schemas related to network traffic data. Defining these
# schemas provides a structured and validated way to handle the various forms of traffic data
# that the application might process or expose. For example, you could define models for raw
# packet data, aggregated traffic metrics, or flow records. This ensures data consistency
# and provides clear documentation for data structures used throughout the application.
#
# Example Usage:
#
# from pydantic import BaseModel
# from datetime import datetime
#
# class TrafficRecord(BaseModel):
#     source_ip: str
#     destination_ip: str
#     port: int
#     timestamp: datetime
#     protocol: str
#
