import uuid
from datetime import datetime

from pydantic import BaseModel, IPvAnyAddress


class ServerCreate(BaseModel):
    name: str
    ip_address: str
    group_name: str | None = None
    tags: list[str] = []
    ping_interval: int = 60
    is_active: bool = True


class ServerUpdate(BaseModel):
    name: str | None = None
    ip_address: str | None = None
    group_name: str | None = None
    tags: list[str] | None = None
    ping_interval: int | None = None
    is_active: bool | None = None


class ServerResponse(BaseModel):
    id: uuid.UUID
    name: str
    ip_address: str
    group_name: str | None
    tags: list[str]
    ping_interval: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServerWithStatus(ServerResponse):
    current_status: str | None = None  # "up", "down", "unknown"
    last_latency_ms: float | None = None
    last_check: datetime | None = None
