from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.history import ChannelHistoryResponse, SavedChannelResponse
from app.services.history_service import HistoryService

router = APIRouter()


@router.get("/channels", response_model=ChannelHistoryResponse)
async def list_my_channels(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChannelHistoryResponse:
    return await HistoryService(session=session).list_user_channels(user_id=current_user.id)


@router.get("/channels/{channel_id}", response_model=SavedChannelResponse)
async def get_my_saved_channel(
    channel_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> SavedChannelResponse:
    saved_channel = await HistoryService(session=session).get_saved_channel(
        user_id=current_user.id,
        channel_id=channel_id,
    )
    if saved_channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved channel not found")
    return saved_channel
