from fastapi import APIRouter

from app.api.v1.routes import channels, health, jobs

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(channels.router, prefix="/channels", tags=["channels"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
