# ContentMate Architecture

## Current implementation scope

Phase 1 and Phase 2 establish the backend orchestrator, relational schema, a Redis-backed queue foundation, YouTube ingestion, transcript retrieval, and transcript-driven channel analysis.

## Core runtime pieces

- `apps/api/app/main.py`: FastAPI entrypoint
- `apps/api/app/api/v1/routes`: versioned API routes
- `apps/api/app/services/youtube_service.py`: orchestration layer for channel/video sync
- `apps/api/app/services/transcript_service.py`: transcript fetch, cleaning, and persistence
- `apps/api/app/services/analysis_service.py`: channel-level insight generation
- `apps/api/app/integrations/youtube/client.py`: yt-dlp-based YouTube metadata client
- `apps/api/app/integrations/transcript/client.py`: transcript provider wrapper
- `apps/api/app/db/models`: SQLAlchemy models
- `apps/api/alembic`: database migration history
- `apps/api/app/workers/queue.py`: job status placeholder built on Redis

## Planned next steps

- transcript retrieval workers
- richer LLM-based analysis and trend services
- OpenAI-powered content generation
- Next.js frontend
- agentic roadmap: see `docs/agentic-roadmap.md`
