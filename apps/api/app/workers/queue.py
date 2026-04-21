from uuid import uuid4

from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()

JOB_STATUS_PREFIX = "contentmate:jobs:"
CHANNEL_JOB_PREFIX = "contentmate:channel-sync:"


def get_redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def enqueue_channel_sync_job(channel_id: str) -> str:
    job_id = await create_job(job_namespace="channel-sync", resource_id=channel_id)
    redis = get_redis_client()
    await redis.set(f"{CHANNEL_JOB_PREFIX}{channel_id}", "queued", ex=86400)
    await redis.aclose()
    return job_id


async def create_job(job_namespace: str, resource_id: str) -> str:
    job_id = f"{job_namespace}:{uuid4()}"
    redis = get_redis_client()
    await redis.set(f"{JOB_STATUS_PREFIX}{job_id}", "queued", ex=86400)
    await redis.set(f"contentmate:{job_namespace}:{resource_id}", "queued", ex=86400)
    await redis.aclose()
    return job_id


async def set_job_status(job_id: str, status: str) -> None:
    redis = get_redis_client()
    await redis.set(f"{JOB_STATUS_PREFIX}{job_id}", status, ex=86400)
    await redis.aclose()


async def get_job_status(channel_id: str) -> str:
    redis = get_redis_client()
    status = await redis.get(f"{CHANNEL_JOB_PREFIX}{channel_id}")
    await redis.aclose()
    return status or "unknown"


async def get_job_status_by_job_id(job_id: str) -> str:
    redis = get_redis_client()
    status = await redis.get(f"{JOB_STATUS_PREFIX}{job_id}")
    await redis.aclose()
    return status or "unknown"
