import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.rate_limit import enforce_pipeline_rate_limit
from app.db.models.user import User
from app.db.session import get_db_session
from app.schemas.pipeline import RunPipelineRequest, RunPipelineResponse
from app.services.credit_service import CreditService, InsufficientCreditsError
from app.services.pipeline_service import PipelineRunError, PipelineService
from app.services.usage_service import UsageLimitExceededError, UsageService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/run", response_model=RunPipelineResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_channel_pipeline(
    payload: RunPipelineRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> RunPipelineResponse:
    request_id = getattr(request.state, "request_id", "-")
    logger.debug(
        "pipeline.route.request request_id=%s user_id=%s channel_url=%s "
        "include_videos=%s include_streams=%s include_shorts=%s "
        "force_transcript_refresh=%s force_ideas_refresh=%s",
        request_id,
        current_user.id,
        payload.channel_url,
        payload.include_videos,
        payload.include_streams,
        payload.include_shorts,
        payload.force_transcript_refresh,
        payload.force_ideas_refresh,
    )
    await enforce_pipeline_rate_limit(request)
    usage_service = UsageService(session=session)
    credit_service = CreditService(session=session)
    status_snapshot = await usage_service.get_analysis_status(user_id=current_user.id)
    use_credit = False
    try:
        await usage_service.assert_can_run_analysis(user_id=current_user.id)
    except UsageLimitExceededError as exc:
        if not status_snapshot.unlimited_access:
            credit_status = await credit_service.get_credit_status(user_id=current_user.id)
            if credit_status.balance > 0:
                use_credit = True
                logger.debug(
                    "pipeline.route.credit_fallback request_id=%s user_id=%s credits=%s",
                    request_id,
                    current_user.id,
                    credit_status.balance,
                )
            else:
                logger.debug(
                    "pipeline.route.rate_limited request_id=%s user_id=%s detail=%s",
                    request_id,
                    current_user.id,
                    str(exc),
                )
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Daily free limit reached. Buy credits to continue.",
                ) from exc
        else:
            logger.debug(
                "pipeline.route.rate_limited request_id=%s user_id=%s detail=%s",
                request_id,
                current_user.id,
                str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
            ) from exc

    service = PipelineService(session=session)
    try:
        response = await service.run_channel_pipeline(
            channel_url=str(payload.channel_url),
            user_id=current_user.id,
            force_transcript_refresh=payload.force_transcript_refresh,
            force_ideas_refresh=payload.force_ideas_refresh,
            include_videos=payload.include_videos,
            include_streams=payload.include_streams,
            include_shorts=payload.include_shorts,
        )
    except PipelineRunError as exc:
        logger.exception(
            "pipeline.route.failed request_id=%s user_id=%s channel_url=%s",
            request_id,
            current_user.id,
            payload.channel_url,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not status_snapshot.unlimited_access:
        if use_credit:
            try:
                await credit_service.consume_analysis_credit(
                    user_id=current_user.id,
                    reference_id=str(payload.channel_url),
                )
            except InsufficientCreditsError as exc:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=str(exc),
                ) from exc
        else:
            await usage_service.record_analysis(
                user_id=current_user.id,
                resource_id=str(payload.channel_url),
            )
    logger.debug(
        "pipeline.route.response request_id=%s user_id=%s channel_id=%s "
        "job_id=%s transcript_fetched=%s transcript_failed=%s "
        "analyzed_videos=%s analyzed_transcripts=%s ideas_model=%s used_credit=%s",
        request_id,
        current_user.id,
        response.channel_sync.channel.id,
        response.job_id,
        response.transcript_sync.fetched_transcripts,
        response.transcript_sync.failed_transcripts,
        response.analysis.result.analyzed_video_count,
        response.analysis.result.analyzed_transcript_count,
        response.ideas.model_name,
        use_credit,
    )
    return response
