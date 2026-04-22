from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db_session
from app.repositories.channel_repository import ChannelRepository
from app.schemas.ideas import (
    ContentIdeasResponse,
    GenerateIdeasRequest,
    GenerateIdeasResponse,
)
from app.services.ideas_service import IdeasGenerationError, IdeasService

router = APIRouter()


@router.post(
    "/channels/{channel_id}/ideas/generate",
    response_model=GenerateIdeasResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_channel_ideas(
    channel_id: UUID,
    payload: GenerateIdeasRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> GenerateIdeasResponse:
    channel = await ChannelRepository(session=session).get_by_id(str(channel_id))
    if channel is None or channel.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    service = IdeasService(session=session)
    try:
        return await service.generate_channel_ideas(
            channel_id=channel_id,
            force_refresh=payload.force_refresh,
        )
    except IdeasGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/channels/{channel_id}/ideas", response_model=ContentIdeasResponse)
async def get_channel_ideas(
    channel_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ContentIdeasResponse:
    channel = await ChannelRepository(session=session).get_by_id(str(channel_id))
    if channel is None or channel.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ideas not found")

    service = IdeasService(session=session)
    ideas = await service.get_channel_ideas(channel_id=channel_id)
    if ideas is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ideas not found")
    return ideas
