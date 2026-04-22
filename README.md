# ContentMate

ContentMate is an AI-powered YouTube content assistant. It can ingest a YouTube channel, fetch a long-form video transcript, analyze the channel with OpenAI, generate content ideas, and present the full workflow in a small web app.

## Current capabilities

- FastAPI application with versioned API routes
- PostgreSQL persistence for users, channels, videos, transcripts, and generated content
- Alembic migration for the initial schema
- Redis-backed job status placeholder for upcoming async transcript and analysis workers
- yt-dlp integration to resolve a channel URL, fetch channel details, and store the longest discovered video over 5 minutes
- Transcript retrieval using `yt-dlp`, with `youtube-transcript-api` fallback
- Transcript cleaning plus chunk preview generation
- OpenAI-powered structured channel analysis
- OpenAI-powered structured content idea generation
- End-to-end pipeline endpoint for channel sync, transcript fetch, analysis, and ideas
- Next.js web app for running and viewing the pipeline

## Local development

1. Copy `.env.example` to `.env` and fill in local secrets such as `OPENAI_API_KEY`.
   For Google sign-in, create a Google OAuth web client. Set `GOOGLE_CLIENT_ID`
   in the API env and `NEXT_PUBLIC_GOOGLE_CLIENT_ID` in the web env.
2. Start infrastructure:

```bash
cd infra
docker compose up -d postgres redis
```

3. Install the API package:

```bash
cd apps/api
pip install -e .
```

4. Run the migration:

```bash
alembic upgrade head
```

5. Start the API:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

6. Start the web app in a second terminal:

```bash
cd apps/web
npm install
npm run dev
```

The web app defaults to `http://127.0.0.1:8000/api/v1`. To override it, set:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_google_oauth_web_client_id.apps.googleusercontent.com
```

For local Next.js development, put the `NEXT_PUBLIC_*` values in `apps/web/.env.local`.

## Current endpoints

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `POST /api/v1/pipeline/run`
- `POST /api/v1/channels/analyze`
- `GET /api/v1/channels/{channel_id}`
- `GET /api/v1/channels/{channel_id}/videos`
- `POST /api/v1/channels/{channel_id}/refresh`
- `GET /api/v1/channels/{channel_id}/sync-status`
- `POST /api/v1/channels/{channel_id}/transcripts/fetch`
- `POST /api/v1/videos/{video_id}/transcript/fetch`
- `GET /api/v1/videos/{video_id}/transcript`
- `POST /api/v1/channels/{channel_id}/analysis/run`
- `GET /api/v1/channels/{channel_id}/analysis`
- `POST /api/v1/channels/{channel_id}/ideas/generate`
- `GET /api/v1/channels/{channel_id}/ideas`
- `GET /api/v1/jobs/{job_id}`

## Suggested flow

1. Open the web app at `http://localhost:3000`.
2. Enter a YouTube channel URL.
3. Run the pipeline to sync the longest discovered video over 5 minutes, fetch transcript chunks, analyze the channel, and generate video/shorts ideas.
