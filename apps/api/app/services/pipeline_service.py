from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.channel import ChannelSyncResponse
from app.schemas.pipeline import RunPipelineResponse
from app.services.analysis_service import AnalysisService, ChannelAnalysisNotFoundError
from app.services.ideas_service import IdeasGenerationError, IdeasService
from app.services.transcript_service import TranscriptService, VideoNotFoundError
from app.services.youtube_service import ChannelNotFoundError, YouTubeService
from app.workers.queue import create_job, enqueue_channel_sync_job, set_job_status


class PipelineRunError(Exception):
    pass


class PipelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.youtube_service = YouTubeService(session=session)
        self.transcript_service = TranscriptService(session=session)
        self.analysis_service = AnalysisService(session=session)
        self.ideas_service = IdeasService(session=session)

    async def run_channel_pipeline(
        self,
        channel_url: str,
        user_id: str,
        force_transcript_refresh: bool = False,
        force_ideas_refresh: bool = True,
    ) -> RunPipelineResponse:
        job_id = await create_job(job_namespace="pipeline", resource_id=channel_url)
        await set_job_status(job_id=job_id, status="processing")

        try:
            sync_result = await self.youtube_service.sync_channel_from_url(
                channel_url,
                user_id=user_id,
            )
            channel_job_id = await enqueue_channel_sync_job(channel_id=sync_result.channel.id)
            channel_sync = ChannelSyncResponse(
                job_id=channel_job_id,
                channel=sync_result.channel,
                videos=sync_result.videos,
            )

            transcript_sync = await self.transcript_service.fetch_transcripts_for_channel(
                channel_id=sync_result.channel.id,
                include_existing=force_transcript_refresh,
                include_text=False,
            )
            if transcript_sync.fetched_transcripts == 0 and all(
                transcript.status != "completed" for transcript in transcript_sync.transcripts
            ):
                failures = [
                    f"{transcript.video_id}: {transcript.error_message or transcript.status}"
                    for transcript in transcript_sync.transcripts
                ]
                failure_detail = "; ".join(failures) or "No videos were processed."
                raise PipelineRunError(
                    "No completed transcripts available after transcript fetch. "
                    f"Transcript failures: {failure_detail}"
                )

            analysis_response = await self.analysis_service.run_channel_analysis(
                channel_id=sync_result.channel.id,
                fetch_missing_transcripts=False,
                force_transcript_refresh=False,
            )
            ideas_response = await self.ideas_service.generate_channel_ideas(
                channel_id=sync_result.channel.id,
                force_refresh=force_ideas_refresh,
            )
        except (
            PipelineRunError,
            ChannelNotFoundError,
            VideoNotFoundError,
            ChannelAnalysisNotFoundError,
            IdeasGenerationError,
        ) as exc:
            await set_job_status(job_id=job_id, status="failed")
            raise PipelineRunError(str(exc)) from exc

        await set_job_status(job_id=job_id, status="completed")
        return RunPipelineResponse(
            job_id=job_id,
            channel_sync=channel_sync,
            transcript_sync=transcript_sync,
            analysis=analysis_response.analysis,
            ideas=ideas_response.ideas,
        )
