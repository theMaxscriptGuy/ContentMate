import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.generated_content import GeneratedContent
from app.integrations.openai.analysis_client import OpenAIAnalysisClient, OpenAIAnalysisError
from app.repositories.channel_repository import ChannelRepository
from app.schemas.agent_workflow import AgentEvidencePackage
from app.schemas.analysis import (
    ChannelAnalysisPayload,
    ChannelAnalysisResponse,
    CreatorProfile,
    TopicInsight,
)
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
                "source_kind": evidence.workflow_meta.source_kind,
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
            creator_profile=self._build_creator_profile(evidence, titles, joined_text),
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

    @staticmethod
    def _build_creator_profile(
        evidence: AgentEvidencePackage,
        titles: list[str],
        joined_text: str,
    ) -> CreatorProfile:
        title_text = " ".join(titles).lower()
        body_text = joined_text.lower()
        combined = f"{title_text} {body_text}".strip()

        if any(word in combined for word in ["funny", "reaction", "fails", "glitch", "challenge"]):
            archetype = "Entertainment-led personality host"
            content_style = "High-energy, moment-driven content built around reactions, spectacle, or shareable moments."
            packaging_style = "Bold, curiosity-led packaging with punchy hooks and fast emotional payoff."
        elif any(word in combined for word in ["guide", "tutorial", "how to", "explained", "tips"]):
            archetype = "Teacher-operator"
            content_style = "Practical, instructional content that wins by clarity, structure, and useful takeaways."
            packaging_style = "Benefit-led packaging that promises a clear transformation or tactical outcome."
        elif any(word in combined for word in ["news", "update", "trend", "latest", "review"]):
            archetype = "Trend translator"
            content_style = "Topical, timely content that reacts to what is happening now and explains why it matters."
            packaging_style = "Timely, relevance-heavy packaging that leans on urgency and topical curiosity."
        else:
            archetype = "Niche-focused creator"
            content_style = "Consistent niche content built around recurring topics, recognizable framing, and audience familiarity."
            packaging_style = "Clear, niche-specific packaging that balances familiarity with a fresh angle."

        if any(word in combined for word in ["funny", "crazy", "insane", "epic", "hilarious"]):
            tone_profile = "Expressive, entertaining, and punchy."
        elif any(word in combined for word in ["guide", "tutorial", "learn", "explained", "strategy"]):
            tone_profile = "Helpful, instructive, and confidence-building."
        else:
            tone_profile = "Accessible, creator-led, and easy to follow."

        audience_profile = (
            f"{evidence.workflow_meta.analysis_mode.capitalize()} audience fit suggests viewers come for "
            f"{detect_niche(extract_candidate_topics(joined_text), joined_text).lower()} content delivered in this creator's style."
        )

        growth_direction = (
            "Double down on formats that already match the creator's natural delivery style, "
            "while making packaging more repeatable and recognizably theirs."
        )

        return CreatorProfile(
            creator_archetype=archetype,
            content_style=content_style,
            tone_profile=tone_profile,
            audience_profile=audience_profile,
            packaging_style=packaging_style,
            growth_direction=growth_direction,
        )
