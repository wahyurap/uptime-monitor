from fastapi import APIRouter

from app.api.availability import router as availability_router
from app.api.ping_results import router as ping_results_router
from app.api.servers import router as servers_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(servers_router)
api_router.include_router(ping_results_router)
api_router.include_router(availability_router)
