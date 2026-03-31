import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ping_result import DailyAvailability, PingResult
from app.models.server import Server
from app.schemas.availability import AvailabilityResponse, AvailabilitySummary, DowntimeIncident


RANGE_DAYS = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "3months": 90,
    "6months": 180,
    "yearly": 365,
}


async def calculate_availability(
    db: AsyncSession,
    server_id: uuid.UUID,
    range_name: str = "daily",
    start: datetime | None = None,
    end: datetime | None = None,
) -> AvailabilityResponse:
    """Calculate availability for a server over a time range."""
    now = datetime.now(timezone.utc)

    if range_name == "custom" and start and end:
        range_start = start
        range_end = end
    else:
        days = RANGE_DAYS.get(range_name, 1)
        range_start = now - timedelta(days=days)
        range_end = now

    server = await db.get(Server, server_id)

    if range_name == "daily" or (range_name == "custom" and (range_end - range_start).days <= 1):
        # Query directly from ping_results for short ranges
        result = await db.execute(
            select(
                func.count(PingResult.id).label("total"),
                func.count(case((PingResult.is_up == True, 1))).label("success"),  # noqa: E712
                func.avg(case((PingResult.is_up == True, PingResult.latency_ms))).label("avg_latency"),  # noqa: E712
            ).where(
                and_(
                    PingResult.server_id == server_id,
                    PingResult.timestamp >= range_start,
                    PingResult.timestamp <= range_end,
                )
            )
        )
        row = result.one()
        total = row.total or 0
        success = row.success or 0
        avg_latency = round(row.avg_latency, 2) if row.avg_latency else None
    else:
        # Query from daily_availability for longer ranges
        result = await db.execute(
            select(
                func.sum(DailyAvailability.total_pings).label("total"),
                func.sum(DailyAvailability.success_pings).label("success"),
                func.avg(DailyAvailability.avg_latency).label("avg_latency"),
            ).where(
                and_(
                    DailyAvailability.server_id == server_id,
                    DailyAvailability.date >= range_start.date(),
                    DailyAvailability.date <= range_end.date(),
                )
            )
        )
        row = result.one()
        total = row.total or 0
        success = row.success or 0
        avg_latency = round(row.avg_latency, 2) if row.avg_latency else None

    availability_pct = round((success / total) * 100, 4) if total > 0 else 0.0

    # Detect downtime incidents
    incidents = await _detect_downtime_incidents(db, server_id, range_start, range_end)

    return AvailabilityResponse(
        server_id=server_id,
        server_name=server.name if server else "Unknown",
        range=range_name,
        start=range_start,
        end=range_end,
        availability_pct=availability_pct,
        total_pings=total,
        successful_pings=success,
        avg_latency_ms=avg_latency,
        downtime_incidents=incidents,
    )


async def _detect_downtime_incidents(
    db: AsyncSession,
    server_id: uuid.UUID,
    start: datetime,
    end: datetime,
) -> list[DowntimeIncident]:
    """Detect consecutive downtime periods."""
    result = await db.execute(
        select(PingResult.is_up, PingResult.timestamp)
        .where(
            and_(
                PingResult.server_id == server_id,
                PingResult.timestamp >= start,
                PingResult.timestamp <= end,
            )
        )
        .order_by(PingResult.timestamp)
    )
    rows = result.all()

    incidents = []
    incident_start = None

    for is_up, ts in rows:
        if not is_up and incident_start is None:
            incident_start = ts
        elif is_up and incident_start is not None:
            duration = (ts - incident_start).total_seconds() / 60
            incidents.append(DowntimeIncident(start=incident_start, end=ts, duration_minutes=round(duration, 1)))
            incident_start = None

    # If still in a downtime at end of range
    if incident_start is not None:
        incidents.append(DowntimeIncident(start=incident_start, end=None, duration_minutes=None))

    return incidents


async def aggregate_daily(db: AsyncSession, target_date: date | None = None):
    """Aggregate ping_results into daily_availability for a given date."""
    if target_date is None:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    day_start = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    # Get all servers
    servers_result = await db.execute(select(Server.id))
    server_ids = [row[0] for row in servers_result.all()]

    for sid in server_ids:
        result = await db.execute(
            select(
                func.count(PingResult.id).label("total"),
                func.count(case((PingResult.is_up == True, 1))).label("success"),  # noqa: E712
                func.avg(case((PingResult.is_up == True, PingResult.latency_ms))).label("avg_latency"),  # noqa: E712
            ).where(
                and_(
                    PingResult.server_id == sid,
                    PingResult.timestamp >= day_start,
                    PingResult.timestamp < day_end,
                )
            )
        )
        row = result.one()
        if row.total and row.total > 0:
            pct = round((row.success / row.total) * 100, 4)
            avg_lat = round(row.avg_latency, 2) if row.avg_latency else None

            # Upsert
            existing = await db.execute(
                select(DailyAvailability).where(
                    and_(DailyAvailability.server_id == sid, DailyAvailability.date == target_date)
                )
            )
            record = existing.scalar_one_or_none()
            if record:
                record.total_pings = row.total
                record.success_pings = row.success
                record.availability_pct = pct
                record.avg_latency = avg_lat
            else:
                db.add(DailyAvailability(
                    server_id=sid,
                    date=target_date,
                    total_pings=row.total,
                    success_pings=row.success,
                    availability_pct=pct,
                    avg_latency=avg_lat,
                ))

    await db.commit()


async def get_availability_summary(db: AsyncSession) -> list[AvailabilitySummary]:
    """Get availability summary for all servers (dashboard)."""
    now = datetime.now(timezone.utc)
    servers_result = await db.execute(select(Server).where(Server.is_active == True))  # noqa: E712
    servers = servers_result.scalars().all()

    summaries = []
    for server in servers:
        # Current status from last ping
        last_ping_result = await db.execute(
            select(PingResult)
            .where(PingResult.server_id == server.id)
            .order_by(PingResult.timestamp.desc())
            .limit(1)
        )
        last_ping = last_ping_result.scalar_one_or_none()

        current_status = "unknown"
        avg_latency = None
        if last_ping:
            current_status = "up" if last_ping.is_up else "down"
            avg_latency = last_ping.latency_ms

        # Quick availability calculations
        async def _quick_avail(hours: int) -> float | None:
            since = now - timedelta(hours=hours)
            r = await db.execute(
                select(
                    func.count(PingResult.id).label("total"),
                    func.count(case((PingResult.is_up == True, 1))).label("success"),  # noqa: E712
                ).where(
                    and_(
                        PingResult.server_id == server.id,
                        PingResult.timestamp >= since,
                    )
                )
            )
            row = r.one()
            if row.total and row.total > 0:
                return round((row.success / row.total) * 100, 2)
            return None

        avail_24h = await _quick_avail(24)
        avail_7d = await _quick_avail(168)
        avail_30d = await _quick_avail(720)

        summaries.append(AvailabilitySummary(
            server_id=server.id,
            server_name=server.name,
            ip_address=server.ip_address,
            group_name=server.group_name,
            current_status=current_status,
            availability_24h=avail_24h,
            availability_7d=avail_7d,
            availability_30d=avail_30d,
            avg_latency_ms=avg_latency,
        ))

    return summaries
