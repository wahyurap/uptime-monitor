import uuid
from datetime import datetime

from pydantic import BaseModel


class PingResultResponse(BaseModel):
    id: int
    server_id: uuid.UUID
    is_up: bool
    latency_ms: float | None
    timestamp: datetime

    model_config = {"from_attributes": True}


class PingResultPage(BaseModel):
    items: list[PingResultResponse]
    total: int
    page: int
    page_size: int
