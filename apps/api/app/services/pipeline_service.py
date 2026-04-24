import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.pipeline import RunPipelineResponse
from app.services.agent_workflow_service import AgentWorkflowError, AgentWorkflowService
from app.services.analysis_service import AnalysisService, ChannelAnalysisNotFoundError
from app.services.ideas_service import IdeasGenerationError, IdeasService
from app.services.transcript_service import TranscriptService, VideoNotFoundError
from app.services.youtube_service import ChannelNotFoundError, YouTubeService
from app.workers.queue import create_job, set_job_status


class PipelineRunError(Exception):
    pass


logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.youtube_service = YouTubeService(session=session)
        self.transcript_service = TranscriptService(session=session)
        self.analysis_service = AnalysisService(session=session)
        self.ideas_service = IdeasService(session=session)
        self.agent_workflow_service = AgentWorkflowService(session=session)

    async def run_channel_pipeline(
        self,
        channel_url: str,
        user_id: str,
        force_transcript_refresh: bool = False,
        force_ideas_refresh: bool = True,
        include_videos: bool = True,
        include_streams: bool = False,
        include_shorts: bool = False,
    ) -> RunPipelineResponse:
        logger.debug(
            "pipeline.run.start channel_url=%s user_id=%s "
            "include_videos=%s include_streams=%s include_shorts=%s "
            "force_transcript_refresh=%s force_ideas_refresh=%s",
            channel_url,
            user_id,
            include_videos,
            include_streams,
            include_shorts,
            force_transcript_refresh,
            force_ideas_refresh,
        )
        job_id = await create_job(job_namespace="pipeline", resource_id=channel_url)
        await set_job_status(job_id=job_id, status="processing")

        try:
            workflow_response = await self.agent_workflow_service.run(
                channel_url,
                user_id=user_id,
                force_transcript_refresh=force_transcript_refresh,
                force_ideas_refresh=force_ideas_refresh,
                include_videos=include_videos,
                include_streams=include_streams,
                include_shorts=include_shorts,
            )
        except (
            PipelineRunError,
            AgentWorkflowError,
            ChannelNotFoundError,
            VideoNotFoundError,
            ChannelAnalysisNotFoundError,
            IdeasGenerationError,
        ) as exc:
            logger.exception("pipeline.run.failed job_id=%s channel_url=%s", job_id, channel_url)
            await set_job_status(job_id=job_id, status="failed")
            raise PipelineRunError(str(exc)) from exc

        await set_job_status(job_id=job_id, status="completed")
        workflow_response.job_id = job_id
        logger.debug(
            "pipeline.run.completed job_id=%s channel_id=%s "
            "analyzed_videos=%s analyzed_transcripts=%s "
            "token_usage=see agent.workflow.completed",
            job_id,
            workflow_response.channel_sync.channel.id,
            workflow_response.analysis.result.analyzed_video_count,
            workflow_response.analysis.result.analyzed_transcript_count,
        )
        return workflow_response

    async def run_video_pipeline(
        self,
        video_url: str,
        user_id: str,
        force_transcript_refresh: bool = False,
        force_ideas_refresh: bool = True,
    ) -> RunPipelineResponse:
        logger.debug(
            "pipeline.run.start video_url=%s user_id=%s "
            "force_transcript_refresh=%s force_ideas_refresh=%s",
            video_url,
            user_id,
            force_transcript_refresh,
            force_ideas_refresh,
        )
        job_id = await create_job(job_namespace="pipeline", resource_id=video_url)
        await set_job_status(job_id=job_id, status="processing")

        try:
            workflow_response = await self.agent_workflow_service.run_video(
                video_url,
                user_id=user_id,
                force_transcript_refresh=force_transcript_refresh,
                force_ideas_refresh=force_ideas_refresh,
            )
        except (
            PipelineRunError,
            AgentWorkflowError,
            ChannelNotFoundError,
            VideoNotFoundError,
            ChannelAnalysisNotFoundError,
            IdeasGenerationError,
        ) as exc:
            logger.exception("pipeline.run.failed job_id=%s video_url=%s", job_id, video_url)
            await set_job_status(job_id=job_id, status="failed")
            raise PipelineRunError(str(exc)) from exc

        await set_job_status(job_id=job_id, status="completed")
        workflow_response.job_id = job_id
        logger.debug(
            "pipeline.run.completed job_id=%s channel_id=%s "
            "analyzed_videos=%s analyzed_transcripts=%s "
            "token_usage=see agent.workflow.completed",
            job_id,
            workflow_response.channel_sync.channel.id,
            workflow_response.analysis.result.analyzed_video_count,
            workflow_response.analysis.result.analyzed_transcript_count,
        )
        return workflow_response
