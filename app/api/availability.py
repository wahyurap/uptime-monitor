import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.availability import AvailabilityResponse, AvailabilitySummary
from app.services.availability import calculate_availability, get_availability_summary

router = APIRouter(tags=["availability"])


@router.get("/servers/{server_id}/availability", response_model=AvailabilityResponse)
async def server_availability(
    server_id: uuid.UUID,
    range: str = Query("daily", regex="^(daily|weekly|monthly|3months|6months|yearly|custom)$"),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await calculate_availability(db, server_id, range, start, end)


@router.get("/availability/summary", response_model=list[AvailabilitySummary])
async def availability_summary(db: AsyncSession = Depends(get_db)):
    return await get_availability_summary(db)
