import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.generated_content import GeneratedContent
from app.integrations.openai.analysis_client import OpenAIAnalysisClient, OpenAIAnalysisError
from app.repositories.channel_repository import ChannelRepository
from app.schemas.agent_workflow import AgentEvidencePackage
from app.schemas.analysis import ChannelAnalysisPayload, ChannelAnalysisResponse, TopicInsight
from app.schemas.openai_usage import OpenAIUsage
from app.utils.text import (
    build_topic_insights,
    detect_niche,
    extract_candidate_topics,
    infer_content_patterns,
    infer_strengths_and_gaps,
    infer_target_audience,
    infer_tone,
)


class AgentStrategyError(Exception):
    pass


@dataclass(slots=True)
class AgentStrategyResult:
    analysis: ChannelAnalysisResponse
    usage: OpenAIUsage


logger = logging.getLogger(__name__)


class AgentStrategyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.channel_repository = ChannelRepository(session=session)
        self.openai_analysis_client = OpenAIAnalysisClient()

    async def generate_strategy(
        self,
        channel_id: UUID,
        evidence: AgentEvidencePackage,
    ) -> AgentStrategyResult:
        channel = await self.channel_repository.get_by_id(str(channel_id))
        if channel is None:
            raise AgentStrategyError("Channel not found")

        logger.debug(
            "agent.strategy.start channel_id=%s title=%s mode=%s "
            "analyzed_videos=%s analyzed_transcripts=%s",
            channel_id,
            evidence.channel_title,
            evidence.workflow_meta.analysis_mode,
            evidence.workflow_meta.analyzed_video_count,
            evidence.workflow_meta.analyzed_transcript_count,
        )

        video_metadata = [
            {
                "title": video.title,
                "description": video.description,
                "duration_seconds": video.duration_seconds,
                "view_count": video.view_count,
                "like_count": video.like_count,
                "comment_count": video.comment_count,
            }
            for video in evidence.videos
        ]

        try:
            result = self.openai_analysis_client.analyze_channel(
                channel_title=evidence.channel_title,
                videos=video_metadata,
                transcript_text=evidence.joined_transcript_text,
                transcript_coverage_ratio=evidence.workflow_meta.transcript_coverage_ratio,
                analyzed_video_count=evidence.workflow_meta.analyzed_video_count,
                analyzed_transcript_count=evidence.workflow_meta.analyzed_transcript_count,
            )
            payload = result.payload
            model_name = f"openai:{result.model_name}"
            usage = result.usage
            logger.debug(
                "agent.strategy.completed channel_id=%s model=%s source=openai "
                "input_tokens=%s output_tokens=%s total_tokens=%s reasoning_tokens=%s",
                channel_id,
                model_name,
                usage.input_tokens,
                usage.output_tokens,
                usage.total_tokens,
                usage.reasoning_tokens,
            )
        except OpenAIAnalysisError:
            payload = self._build_heuristic_strategy(evidence)
            model_name = "heuristic-v1"
            usage = OpenAIUsage()
            logger.debug(
                "agent.strategy.completed channel_id=%s model=%s source=heuristic",
                channel_id,
                model_name,
            )

        analysis_row = GeneratedContent(
            user_id=channel.user_id,
            channel_id=channel.id,
            content_type="channel_analysis",
            prompt_input={
                "workflow": "langgraph-agentic-v1",
                "platform": evidence.workflow_meta.platform,
                "selected_content_types": evidence.workflow_meta.selected_content_types,
                "transcript_coverage_ratio": evidence.workflow_meta.transcript_coverage_ratio,
                "analyzed_video_count": evidence.workflow_meta.analyzed_video_count,
                "analyzed_transcript_count": evidence.workflow_meta.analyzed_transcript_count,
                "openai_usage": usage.model_dump(),
            },
            result_json=payload.model_dump(),
            status="completed",
            model_name=model_name,
        )
        self.session.add(analysis_row)
        channel.analysis_status = "completed"
        await self.session.commit()
        await self.session.refresh(analysis_row)

        return AgentStrategyResult(
            analysis=ChannelAnalysisResponse(
                id=UUID(analysis_row.id),
                channel_id=UUID(analysis_row.channel_id),
                content_type=analysis_row.content_type,
                status=analysis_row.status,
                model_name=analysis_row.model_name,
                created_at=analysis_row.created_at,
                result=payload,
            ),
            usage=usage,
        )

    def _build_heuristic_strategy(self, evidence: AgentEvidencePackage) -> ChannelAnalysisPayload:
        joined_text = evidence.joined_transcript_text
        titles = [video.title for video in evidence.videos]
        topic_counter = extract_candidate_topics(joined_text)
        primary_topics, secondary_topics = build_topic_insights(topic_counter)
        strengths, gaps = infer_strengths_and_gaps(
            topic_counter,
            evidence.workflow_meta.analyzed_transcript_count,
        )

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
            transcript_coverage_ratio=evidence.workflow_meta.transcript_coverage_ratio,
            analyzed_video_count=evidence.workflow_meta.analyzed_video_count,
            analyzed_transcript_count=evidence.workflow_meta.analyzed_transcript_count,
        )
