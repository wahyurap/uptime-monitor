import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.router import api_router
from app.config import settings
from app.services.availability import get_availability_summary
from app.services.scheduler import start_scheduler, stop_scheduler
from app.database import async_session, get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.app_name)
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("Stopped %s", settings.app_name)


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    async with async_session() as db:
        summaries = await get_availability_summary(db)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "servers": summaries,
        "settings": settings,
    })


@app.get("/server/{server_id}", response_class=HTMLResponse)
async def server_detail(request: Request, server_id: str):
    import uuid
    from sqlalchemy import select, and_
    from datetime import datetime, timedelta, timezone
    from app.models.server import Server
    from app.models.ping_result import PingResult
    from app.services.availability import calculate_availability

    async with async_session() as db:
        sid = uuid.UUID(server_id)
        server = await db.get(Server, sid)
        if not server:
            return HTMLResponse("Server not found", status_code=404)

        availability = await calculate_availability(db, sid, "monthly")

        # Last 100 pings for chart
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(PingResult)
            .where(and_(
                PingResult.server_id == sid,
                PingResult.timestamp >= now - timedelta(hours=24),
            ))
            .order_by(PingResult.timestamp.asc())
            .limit(200)
        )
        pings = result.scalars().all()

        # Daily availability for last 30 days
        from app.models.ping_result import DailyAvailability
        daily_result = await db.execute(
            select(DailyAvailability)
            .where(and_(
                DailyAvailability.server_id == sid,
                DailyAvailability.date >= (now - timedelta(days=30)).date(),
            ))
            .order_by(DailyAvailability.date.asc())
        )
        daily_avails = daily_result.scalars().all()

    return templates.TemplateResponse("server_detail.html", {
        "request": request,
        "server": server,
        "availability": availability,
        "pings": pings,
        "daily_avails": daily_avails,
        "settings": settings,
    })
