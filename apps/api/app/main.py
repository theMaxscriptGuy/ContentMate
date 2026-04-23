from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import RateLimiter, get_client_ip

settings = get_settings()


def _parse_allowed_origins(raw_origins: str) -> list[str]:
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_allowed_origins(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_request_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            body_size = int(content_length)
        except ValueError:
            body_size = settings.max_request_body_bytes + 1
        if body_size > settings.max_request_body_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body is too large."},
            )

    return await call_next(request)


@app.middleware("http")
async def apply_global_rate_limit(request: Request, call_next):
    if not request.url.path.startswith(settings.api_v1_prefix):
        return await call_next(request)

    if request.url.path in {
        f"{settings.api_v1_prefix}/health",
        f"{settings.api_v1_prefix}/ready",
    }:
        return await call_next(request)

    try:
        await RateLimiter().enforce(
            namespace="global-api",
            subject=get_client_ip(request),
            limit=settings.rate_limit_global_requests_per_minute,
            window_seconds=60,
        )
    except HTTPException as exc:
        if exc.status_code == 429:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )
        raise

    return await call_next(request)


app.include_router(api_router, prefix=settings.api_v1_prefix)
