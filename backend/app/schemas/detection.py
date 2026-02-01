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
