from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.pipeline import RunPipelineRequest, RunPipelineResponse
from app.services.pipeline_service import PipelineRunError, PipelineService
from app.services.usage_service import UsageLimitExceededError, UsageService

router = APIRouter()


@router.post("/run", response_model=RunPipelineResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_channel_pipeline(
    payload: RunPipelineRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> RunPipelineResponse:
    usage_service = UsageService(session=session)
    try:
        await usage_service.assert_can_run_analysis(user_id=current_user.id)
    except UsageLimitExceededError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    service = PipelineService(session=session)
    try:
        response = await service.run_channel_pipeline(
            channel_url=str(payload.channel_url),
            user_id=current_user.id,
            force_transcript_refresh=payload.force_transcript_refresh,
            force_ideas_refresh=payload.force_ideas_refresh,
        )
    except PipelineRunError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await usage_service.record_analysis(
        user_id=current_user.id,
        resource_id=str(payload.channel_url),
    )
    return response
