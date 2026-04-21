from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.pipeline import RunPipelineRequest, RunPipelineResponse
from app.services.pipeline_service import PipelineRunError, PipelineService

router = APIRouter()


@router.post("/run", response_model=RunPipelineResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_channel_pipeline(
    payload: RunPipelineRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RunPipelineResponse:
    service = PipelineService(session=session)
    try:
        return await service.run_channel_pipeline(
            channel_url=str(payload.channel_url),
            force_transcript_refresh=payload.force_transcript_refresh,
            force_ideas_refresh=payload.force_ideas_refresh,
        )
    except PipelineRunError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
