from fastapi import APIRouter

from app.api.v1.routes import analysis, auth, channels, health, ideas, jobs, pipeline, transcripts

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(channels.router, prefix="/channels", tags=["channels"])
api_router.include_router(transcripts.router, tags=["transcripts"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(ideas.router, tags=["ideas"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
