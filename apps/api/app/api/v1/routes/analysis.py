from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db_session
from app.repositories.channel_repository import ChannelRepository
from app.schemas.analysis import (
    ChannelAnalysisResponse,
    RunChannelAnalysisRequest,
    RunChannelAnalysisResponse,
)
from app.services.analysis_service import AnalysisService, ChannelAnalysisNotFoundError

router = APIRouter()


@router.post(
    "/channels/{channel_id}/analysis/run",
    response_model=RunChannelAnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_channel_analysis(
    channel_id: UUID,
    payload: RunChannelAnalysisRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> RunChannelAnalysisResponse:
    channel = await ChannelRepository(session=session).get_by_id(str(channel_id))
    if channel is None or channel.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    service = AnalysisService(session=session)
    try:
        return await service.run_channel_analysis(
            channel_id=channel_id,
            fetch_missing_transcripts=payload.fetch_missing_transcripts,
            force_transcript_refresh=payload.force_transcript_refresh,
        )
    except ChannelAnalysisNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/channels/{channel_id}/analysis", response_model=ChannelAnalysisResponse)
async def get_channel_analysis(
    channel_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ChannelAnalysisResponse:
    channel = await ChannelRepository(session=session).get_by_id(str(channel_id))
    if channel is None or channel.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    service = AnalysisService(session=session)
    analysis = await service.get_channel_analysis(channel_id=channel_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis
