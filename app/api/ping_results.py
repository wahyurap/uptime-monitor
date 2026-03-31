import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ping_result import PingResult
from app.schemas.ping_result import PingResultPage, PingResultResponse

router = APIRouter(tags=["ping_results"])


@router.get("/servers/{server_id}/pings", response_model=PingResultPage)
async def list_pings(
    server_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    start: datetime | None = None,
    end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
):
    conditions = [PingResult.server_id == server_id]
    if start:
        conditions.append(PingResult.timestamp >= start)
    if end:
        conditions.append(PingResult.timestamp <= end)

    where = and_(*conditions)

    # Count
    count_result = await db.execute(select(func.count(PingResult.id)).where(where))
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    result = await db.execute(
        select(PingResult)
        .where(where)
        .order_by(PingResult.timestamp.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = result.scalars().all()

    return PingResultPage(
        items=[PingResultResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )
