import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import and_, delete, select

from app.config import settings
from app.database import async_session
from app.models.ping_result import PingResult
from app.models.server import Server
from app.services.availability import aggregate_daily
from app.services.pinger import ping_batch

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def ping_all_servers():
    """Ping all active servers and store results."""
    async with async_session() as db:
        result = await db.execute(select(Server).where(Server.is_active == True))  # noqa: E712
        servers = result.scalars().all()

        if not servers:
            return

        # Batch ping
        hosts = [(str(s.id), s.ip_address) for s in servers]
        batch_size = settings.ping_batch_size

        for i in range(0, len(hosts), batch_size):
            batch = hosts[i : i + batch_size]
            results = await ping_batch(batch, timeout=settings.ping_timeout, retries=settings.ping_retries)

            for server_id, (is_up, latency) in results.items():
                db.add(PingResult(
                    server_id=server_id,
                    is_up=is_up,
                    latency_ms=latency,
                ))

            await db.commit()

        logger.info("Pinged %d servers", len(servers))


async def daily_aggregation_job():
    """Run daily aggregation of ping results."""
    async with async_session() as db:
        await aggregate_daily(db)
    logger.info("Daily aggregation completed")


async def cleanup_old_pings():
    """Remove ping results older than retention period."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.ping_retention_days)
    async with async_session() as db:
        await db.execute(delete(PingResult).where(PingResult.timestamp < cutoff))
        await db.commit()
    logger.info("Cleaned up pings older than %d days", settings.ping_retention_days)


def start_scheduler():
    """Start the background scheduler."""
    # Ping all servers every minute (default interval)
    # max_instances=1 prevents overlapping jobs (important for 90+ servers)
    scheduler.add_job(
        ping_all_servers,
        IntervalTrigger(seconds=settings.default_ping_interval),
        id="ping_all",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping executions
    )

    # Daily aggregation at 00:05 UTC
    scheduler.add_job(
        daily_aggregation_job,
        CronTrigger(hour=0, minute=5),
        id="daily_aggregation",
        replace_existing=True,
    )

    # Cleanup old pings daily at 01:00 UTC
    scheduler.add_job(
        cleanup_old_pings,
        CronTrigger(hour=1, minute=0),
        id="cleanup_old_pings",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
