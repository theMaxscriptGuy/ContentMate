# ContentMate Deployment

## Backend on Railway

Create a Railway project from the GitHub repo and add:

- FastAPI service from this repository
- PostgreSQL service
- Redis service

The API service uses `railway.json`, which points Railway at `infra/docker/api.Dockerfile`,
runs Alembic migrations before deploy, and checks `/api/v1/health`.

Set these API variables in Railway:

```text
APP_ENV=production
APP_DEBUG=false
API_V1_PREFIX=/api/v1
CORS_ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app
POSTGRES_DSN=postgresql+asyncpg://...
REDIS_URL=redis://...
OPENAI_API_KEY=...
OPENAI_ANALYSIS_MODEL=gpt-4.1-mini
OPENAI_ANALYSIS_MAX_TRANSCRIPT_CHARS=60000
GOOGLE_CLIENT_ID=...
AUTH_TOKEN_SECRET=...
AUTH_TOKEN_TTL_SECONDS=604800
DAILY_ANALYSIS_LIMIT=2
YOUTUBE_MIN_DURATION_SECONDS=301
YOUTUBE_SCAN_LIMIT=0
YOUTUBE_CANDIDATE_POOL_SIZE=30
TRANSCRIPT_USE_YTDLP_FALLBACK=true
```

## Frontend on Vercel

Create a Vercel project from the same GitHub repo:

- Root Directory: `apps/web`
- Framework Preset: Next.js
- Build Command: `npm run build`

Set these Vercel variables:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-railway-api-domain.up.railway.app/api/v1
NEXT_PUBLIC_GOOGLE_CLIENT_ID=...
```

## Google OAuth

Add authorized JavaScript origins:

```text
http://localhost:3000
http://127.0.0.1:3000
https://your-vercel-domain.vercel.app
```

## Smoke Test

1. Open the Vercel URL.
2. Sign in with Google.
3. Run one analysis.
4. Confirm the daily usage count decreases.
5. Confirm the analyzed channel appears in My Channels.
6. Open the saved channel from history.
