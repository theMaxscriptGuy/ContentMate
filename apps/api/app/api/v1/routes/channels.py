from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.channel import (
    ChannelAnalysisRequest,
    ChannelDetailResponse,
    ChannelSyncResponse,
    VideoSummary,
)
from app.services.youtube_service import ChannelNotFoundError, YouTubeService
from app.workers.queue import enqueue_channel_sync_job, get_job_status

router = APIRouter()


@router.post("/analyze", response_model=ChannelSyncResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_channel(
    payload: ChannelAnalysisRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ChannelSyncResponse:
    service = YouTubeService(session=session)

    try:
        sync_result = await service.sync_channel_from_url(str(payload.channel_url))
    except ChannelNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    job_id = await enqueue_channel_sync_job(channel_id=sync_result.channel.id)

    return ChannelSyncResponse(
        job_id=job_id,
        channel=sync_result.channel,
        videos=sync_result.videos,
    )


@router.get("/{channel_id}", response_model=ChannelDetailResponse)
async def get_channel(
    channel_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ChannelDetailResponse:
    service = YouTubeService(session=session)
    channel, videos = await service.get_channel_with_videos(channel_id=channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return ChannelDetailResponse(channel=channel, videos=videos)


@router.get("/{channel_id}/videos", response_model=list[VideoSummary])
async def list_channel_videos(
    channel_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[VideoSummary]:
    service = YouTubeService(session=session)
    channel, videos = await service.get_channel_with_videos(channel_id=channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return videos


@router.post("/{channel_id}/refresh", response_model=ChannelSyncResponse, status_code=status.HTTP_202_ACCEPTED)
async def refresh_channel(
    channel_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ChannelSyncResponse:
    service = YouTubeService(session=session)
    refreshed = await service.refresh_channel(channel_id=channel_id)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    job_id = await enqueue_channel_sync_job(channel_id=refreshed.channel.id)
    return ChannelSyncResponse(job_id=job_id, channel=refreshed.channel, videos=refreshed.videos)


@router.get("/{channel_id}/sync-status")
async def get_channel_sync_status(channel_id: UUID) -> dict[str, str | UUID]:
    job_status = await get_job_status(str(channel_id))
    return {"channel_id": channel_id, "status": job_status}
