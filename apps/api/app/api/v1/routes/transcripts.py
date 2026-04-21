from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.transcript import (
    ChannelTranscriptSyncResponse,
    TranscriptRefreshResponse,
    TranscriptResponse,
)
from app.services.transcript_service import TranscriptService, VideoNotFoundError

router = APIRouter()


@router.post(
    "/channels/{channel_id}/transcripts/fetch",
    response_model=ChannelTranscriptSyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def fetch_channel_transcripts(
    channel_id: UUID,
    include_existing: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
) -> ChannelTranscriptSyncResponse:
    service = TranscriptService(session=session)
    try:
        return await service.fetch_transcripts_for_channel(
            channel_id=channel_id,
            include_existing=include_existing,
        )
    except VideoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/videos/{video_id}/transcript/fetch",
    response_model=TranscriptRefreshResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def fetch_video_transcript(
    video_id: UUID,
    force: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
) -> TranscriptRefreshResponse:
    service = TranscriptService(session=session)
    try:
        return await service.fetch_transcript_for_video(video_id=video_id, force=force)
    except VideoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/videos/{video_id}/transcript", response_model=TranscriptResponse)
async def get_video_transcript(
    video_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> TranscriptResponse:
    service = TranscriptService(session=session)
    transcript = await service.get_transcript_for_video(video_id=video_id)
    if transcript is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")
    return transcript
