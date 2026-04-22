from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.generated_content import GeneratedContent
from app.integrations.openai.analysis_client import OpenAIAnalysisClient, OpenAIAnalysisError
from app.repositories.channel_repository import ChannelRepository
from app.repositories.generated_content_repository import GeneratedContentRepository
from app.schemas.analysis import (
    ChannelAnalysisPayload,
    ChannelAnalysisResponse,
    RunChannelAnalysisResponse,
    TopicInsight,
)
from app.services.transcript_service import TranscriptService
from app.utils.text import (
    build_topic_insights,
    detect_niche,
    extract_candidate_topics,
    infer_content_patterns,
    infer_strengths_and_gaps,
    infer_target_audience,
    infer_tone,
)
from app.workers.queue import create_job, set_job_status


class ChannelAnalysisNotFoundError(Exception):
    pass


@dataclass(slots=True)
class _TranscriptRunStats:
    fetched: int
    failed: int


class AnalysisService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.channel_repository = ChannelRepository(session=session)
        self.generated_content_repository = GeneratedContentRepository(session=session)
        self.transcript_service = TranscriptService(session=session)
        self.openai_analysis_client = OpenAIAnalysisClient()

    async def run_channel_analysis(
        self,
        channel_id: UUID,
        fetch_missing_transcripts: bool = True,
        force_transcript_refresh: bool = False,
    ) -> RunChannelAnalysisResponse:
        channel = await self.channel_repository.get_by_id(str(channel_id))
        if channel is None:
            raise ChannelAnalysisNotFoundError("Channel not found")

        transcript_stats = _TranscriptRunStats(fetched=0, failed=0)
        if fetch_missing_transcripts:
            transcript_sync = await self.transcript_service.fetch_transcripts_for_channel(
                channel_id=channel_id,
                include_existing=force_transcript_refresh,
            )
            transcript_stats = _TranscriptRunStats(
                fetched=transcript_sync.fetched_transcripts,
                failed=transcript_sync.failed_transcripts,
            )

        job_id = await create_job(job_namespace="analysis", resource_id=str(channel_id))
        await set_job_status(job_id=job_id, status="processing")

        videos = await self.channel_repository.list_active_videos_for_channel(str(channel_id))
        transcripts = []
        for video in videos:
            transcript = await self.transcript_service.get_transcript_record(video.id)
            if transcript and transcript.cleaned_text:
                transcripts.append((video, transcript))

        if not transcripts:
            await set_job_status(job_id=job_id, status="failed")
            raise ChannelAnalysisNotFoundError(
                "No transcripts available to analyze for this channel"
            )

        joined_text = "\n\n".join(transcript.cleaned_text or "" for _, transcript in transcripts)
        transcript_coverage_ratio = round(len(transcripts) / max(len(videos), 1), 2)
        video_metadata = [
            {
                "title": video.title,
                "description": video.description,
                "duration_seconds": video.duration_seconds,
                "view_count": video.view_count,
                "like_count": video.like_count,
                "comment_count": video.comment_count,
            }
            for video, _ in transcripts
        ]

        try:
            analysis_result = self.openai_analysis_client.analyze_channel(
                channel_title=channel.title,
                videos=video_metadata,
                transcript_text=joined_text,
                transcript_coverage_ratio=transcript_coverage_ratio,
                analyzed_video_count=len(videos),
                analyzed_transcript_count=len(transcripts),
            )
            payload = analysis_result.payload
            model_name = f"openai:{analysis_result.model_name}"
        except OpenAIAnalysisError:
            payload = self._build_heuristic_analysis(
                joined_text=joined_text,
                titles=[video.title for video, _ in transcripts],
                transcript_coverage_ratio=transcript_coverage_ratio,
                analyzed_video_count=len(videos),
                analyzed_transcript_count=len(transcripts),
            )
            model_name = "heuristic-v1"

        analysis_row = GeneratedContent(
            user_id=channel.user_id,
            channel_id=channel.id,
            content_type="channel_analysis",
            prompt_input={
                "transcript_count": len(transcripts),
                "video_count": len(videos),
                "openai_configured": self.openai_analysis_client.is_configured(),
            },
            result_json=payload.model_dump(),
            status="completed",
            model_name=model_name,
        )
        self.session.add(analysis_row)
        channel.analysis_status = "completed"
        await self.session.commit()
        await self.session.refresh(analysis_row)
        await set_job_status(job_id=job_id, status="completed")

        return RunChannelAnalysisResponse(
            job_id=job_id,
            analysis=self._serialize_analysis(analysis_row),
            fetched_transcripts=transcript_stats.fetched,
            failed_transcripts=transcript_stats.failed,
        )

    def _build_heuristic_analysis(
        self,
        joined_text: str,
        titles: list[str],
        transcript_coverage_ratio: float,
        analyzed_video_count: int,
        analyzed_transcript_count: int,
    ) -> ChannelAnalysisPayload:
        topic_counter = extract_candidate_topics(joined_text)
        primary_topics, secondary_topics = build_topic_insights(topic_counter)

        strengths, gaps = infer_strengths_and_gaps(topic_counter, analyzed_transcript_count)

        return ChannelAnalysisPayload(
            niche=detect_niche(topic_counter, joined_text),
            primary_topics=[
                TopicInsight(topic=topic, mentions=count) for topic, count in primary_topics
            ],
            secondary_topics=[
                TopicInsight(topic=topic, mentions=count) for topic, count in secondary_topics
            ],
            tone=infer_tone(joined_text),
            target_audience=infer_target_audience(joined_text, titles),
            content_patterns=infer_content_patterns(titles),
            strengths=strengths,
            gaps=gaps,
            transcript_coverage_ratio=transcript_coverage_ratio,
            analyzed_video_count=analyzed_video_count,
            analyzed_transcript_count=analyzed_transcript_count,
        )

    async def get_channel_analysis(self, channel_id: UUID) -> ChannelAnalysisResponse | None:
        record = await self.generated_content_repository.get_latest_for_channel(
            channel_id=str(channel_id),
            content_type="channel_analysis",
        )
        if record is None or not record.result_json:
            return None
        return self._serialize_analysis(record)

    @staticmethod
    def _serialize_analysis(record: GeneratedContent) -> ChannelAnalysisResponse:
        return ChannelAnalysisResponse(
            id=UUID(record.id),
            channel_id=UUID(record.channel_id),
            content_type=record.content_type,
            status=record.status,
            model_name=record.model_name,
            created_at=record.created_at,
            result=ChannelAnalysisPayload.model_validate(record.result_json),
        )
