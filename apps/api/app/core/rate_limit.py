import logging
from collections.abc import Callable

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis

from app.core.config import get_settings
from app.workers.queue import get_redis_client

settings = get_settings()
logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, redis_factory: Callable[[], Redis] = get_redis_client) -> None:
        self.redis_factory = redis_factory

    async def enforce(
        self,
        *,
        namespace: str,
        subject: str,
        limit: int,
        window_seconds: int,
    ) -> None:
        if limit <= 0:
            return

        redis = self.redis_factory()
        key = f"contentmate:rate-limit:{namespace}:{subject}"
        try:
            current_count = await redis.incr(key)
            if current_count == 1:
                await redis.expire(key, window_seconds)
            if current_count > limit:
                ttl = await redis.ttl(key)
                logger.warning(
                    "rate_limit_exceeded namespace=%s subject=%s limit=%s window_seconds=%s ttl=%s",
                    namespace,
                    subject,
                    limit,
                    window_seconds,
                    ttl,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please wait and try again.",
                    headers={"Retry-After": str(max(ttl, 1))},
                )
        finally:
            await redis.aclose()


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


async def enforce_auth_rate_limit(request: Request) -> None:
    await RateLimiter().enforce(
        namespace="auth-google",
        subject=get_client_ip(request),
        limit=settings.rate_limit_auth_requests_per_minute,
        window_seconds=60,
    )


async def enforce_pipeline_rate_limit(request: Request) -> None:
    await RateLimiter().enforce(
        namespace="pipeline-run",
        subject=get_client_ip(request),
        limit=settings.rate_limit_pipeline_requests_per_hour,
        window_seconds=3600,
    )
