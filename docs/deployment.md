# ContentMate v1 Production Deployment Runbook

This document captures the v1 production setup for deploying ContentMate from the
`main` branch.

Production topology:

- Frontend: Vercel, Next.js app from `apps/web`
- Backend API: Railway, FastAPI app from `apps/api`
- Database: Railway PostgreSQL
- Cache/queue: Railway Redis
- Public domain: `https://www.contentmatepro.com`
- Backend domain: Railway generated domain, for example
  `https://contentmate-production.up.railway.app`

Do not commit real secrets. Set production secrets only in Railway, Vercel, and
Google Cloud.

## 1. GitHub Checkpoint

Before deploying, confirm the branch is clean and pushed.

```bash
git status --short --branch
git log -5 --oneline
git push origin main
```

Create a checkpoint commit when needed:

```bash
git add .
git commit -m "Describe production checkpoint"
git push origin main
```

Optional v1 tag:

```bash
git tag v1-prod
git push origin v1-prod
```

## 2. Railway Backend

Create a new Railway project:

1. Railway -> New Project.
2. Deploy from GitHub repo.
3. Select the ContentMate repo and `main` branch.
4. The service should use `railway.json`.
5. Add a PostgreSQL service.
6. Add a Redis service.

The backend Dockerfile is:

```text
infra/docker/api.Dockerfile
```

The Railway config runs:

```text
alembic upgrade head
```

before deployment and checks:

```text
/api/v1/health
```

## 3. Railway Variables

Set these on the GitHub-backed API service, not on the Postgres or Redis service.

Use Railway references for database services:

```text
DATABASE_URL=${{ Postgres.DATABASE_URL }}
REDIS_URL=${{ Redis.REDIS_URL }}
```

If the Railway service names differ, replace `Postgres` or `Redis` with the exact
service name shown in Railway.

Required API variables:

```text
APP_ENV=production
APP_DEBUG=false
API_V1_PREFIX=/api/v1
DATABASE_URL=${{ Postgres.DATABASE_URL }}
REDIS_URL=${{ Redis.REDIS_URL }}
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
CORS_ALLOWED_ORIGINS=https://www.contentmatepro.com,https://contentmatepro.com
```

For a temporary Vercel preview domain, include that exact origin too:

```text
CORS_ALLOWED_ORIGINS=https://your-preview.vercel.app,https://www.contentmatepro.com,https://contentmatepro.com
```

Redeploy Railway after variable changes.

## 4. Railway Public Domain

1. Open the Railway API service.
2. Settings -> Networking.
3. Generate a public service domain.
4. If Railway asks for a port, use the port that responds for the deployed service.
   In v1, the working generated domain was on port `8080`.
5. Test:

```text
https://your-railway-domain/api/v1/health
```

Expected response includes `status: ok`.

Use this backend URL in Vercel:

```text
https://your-railway-domain/api/v1
```

## 5. Vercel Frontend

Create a Vercel project from the same GitHub repo.

Use these settings:

```text
Root Directory: apps/web
Framework Preset: Next.js
Build Command: npm run build
Install Command: npm install
Output Directory: empty/default
```

Do not set Output Directory to `public` or `.next`; Vercel handles Next.js output
automatically when the root directory is `apps/web`.

Set these Vercel variables:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-railway-domain/api/v1
NEXT_PUBLIC_GOOGLE_CLIENT_ID=...
```

Redeploy Vercel after changing either variable.

## 6. Google OAuth

In Google Cloud Console:

1. APIs & Services -> Credentials.
2. Open the OAuth 2.0 Web Client.
3. Add Authorized JavaScript origins.

For production:

```text
https://www.contentmatepro.com
https://contentmatepro.com
```

For local development:

```text
http://localhost:3000
http://127.0.0.1:3000
```

For a temporary Vercel preview domain, add the exact browser origin:

```text
https://your-preview.vercel.app
```

Rules:

- Include `https://`.
- Do not include a trailing slash.
- Do not include `/api/v1` or any path.
- The frontend `NEXT_PUBLIC_GOOGLE_CLIENT_ID` and backend `GOOGLE_CLIENT_ID`
  must be the same client ID.

## 7. GoDaddy DNS For `contentmatepro.com`

In Vercel:

1. Project -> Settings -> Domains.
2. Add `contentmatepro.com`.
3. Add `www.contentmatepro.com`.
4. The v1 setup redirects `contentmatepro.com` to `www.contentmatepro.com`.

In GoDaddy DNS, add/update:

```text
Type: A
Name: @
Value: 76.76.21.21
TTL: default
```

```text
Type: CNAME
Name: www
Value: cname.vercel-dns.com
TTL: default
```

Remove conflicting GoDaddy parked records for `@` and `www`, such as old A
records or CNAMEs that point somewhere else.

Return to Vercel and click Refresh for both domains. DNS can take a few minutes,
and sometimes longer.

## 8. Final Production Checks

Open:

```text
https://www.contentmatepro.com
```

Test:

1. Page loads from the custom domain.
2. Google sign-in works.
3. Analyze requires Google login.
4. A channel analysis runs.
5. Daily usage limit shows and enforces 2 analyses/user/day.
6. My Channels/history shows saved user data.
7. Opening a saved channel restores results.

Also test backend health:

```text
https://your-railway-domain/api/v1/health
```

## 9. Common Issues

### Railway tries localhost Postgres

Symptom:

```text
connection to server at "localhost", port 5432 failed
```

Fix:

Set `DATABASE_URL` on the API service:

```text
DATABASE_URL=${{ Postgres.DATABASE_URL }}
```

### Vercel cannot find Next.js

Symptom:

```text
No Next.js version detected
```

Fix:

Set Vercel Root Directory to:

```text
apps/web
```

### Vercel looks for `public`

Symptom:

```text
No Output Directory named "public" found
```

Fix:

Clear Output Directory. Keep it empty/default.

### Google origin mismatch

Symptom:

```text
Error 400: origin_mismatch
```

Fix:

Add the exact frontend origin to Google OAuth Authorized JavaScript origins.

### Browser CORS error

Symptom:

```text
No 'Access-Control-Allow-Origin' header
```

Fix:

Add the exact frontend origin to Railway `CORS_ALLOWED_ORIGINS`, then redeploy
Railway.

### Backend returns 401 during Google login

Fix:

Make sure Railway has:

```text
GOOGLE_CLIENT_ID=...
```

and it matches Vercel:

```text
NEXT_PUBLIC_GOOGLE_CLIENT_ID=...
```

### Transcript fetching fails in production

Railway/shared hosting IPs can be blocked or rate-limited by YouTube transcript
endpoints. ContentMate v1 tries:

1. `youtube-transcript-api`
2. `yt-dlp` fallback

If transcripts fail, v1 continues with metadata-based analysis from video titles
and descriptions instead of failing the full pipeline.

## 10. Security Checklist

Before public sharing:

1. Rotate any OpenAI key, Google secret, or YouTube key that appeared in local
   files, screenshots, logs, or chat.
2. Confirm `.env`, `apps/api/.env`, and `apps/web/.env.local` are not committed.
3. Keep secrets only in Railway/Vercel/Google Cloud.
4. Confirm GitHub does not contain obvious committed secrets:

```bash
rg -n "sk-proj-|GOCSPX|AIza|client_secret" . \
  --glob '!.env' \
  --glob '!apps/api/.env' \
  --glob '!apps/web/.env.local' \
  --glob '!apps/web/node_modules/**' \
  --glob '!apps/web/.next/**' \
  --glob '!apps/api/.venv/**'
```
