import uuid
from datetime import datetime

from pydantic import BaseModel


class DowntimeIncident(BaseModel):
    start: datetime
    end: datetime | None
    duration_minutes: float | None


class AvailabilityResponse(BaseModel):
    server_id: uuid.UUID
    server_name: str
    range: str
    start: datetime
    end: datetime
    availability_pct: float
    total_pings: int
    successful_pings: int
    avg_latency_ms: float | None
    downtime_incidents: list[DowntimeIncident]


class DailyAvailabilityResponse(BaseModel):
    date: str
    availability_pct: float
    total_pings: int
    success_pings: int
    avg_latency: float | None

    model_config = {"from_attributes": True}


class AvailabilitySummary(BaseModel):
    server_id: uuid.UUID
    server_name: str
    ip_address: str
    group_name: str | None
    current_status: str
    availability_24h: float | None
    availability_7d: float | None
    availability_30d: float | None
    avg_latency_ms: float | None
