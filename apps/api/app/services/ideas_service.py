from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.generated_content import GeneratedContent
from app.integrations.openai.ideas_client import (
    OpenAIIdeasClient,
    OpenAIIdeasError,
    OpenAIParsedResult,
)
from app.integrations.trends.client import TrendClient, TrendProviderError
from app.repositories.channel_repository import ChannelRepository
from app.repositories.generated_content_repository import GeneratedContentRepository
from app.schemas.analysis import ChannelAnalysisPayload
from app.schemas.ideas import (
    ContentIdeasPayload,
    ContentIdeasResponse,
    GenerateIdeasResponse,
    LongformIdeasPayload,
    PlannerIdeasPayload,
    ShortformIdeasPayload,
)
from app.workers.queue import create_job, set_job_status


class IdeasGenerationError(Exception):
    pass


@dataclass(slots=True)
class IdeasGenerationContext:
    channel: object
    analysis_row: GeneratedContent
    analysis: ChannelAnalysisPayload
    trend_geo: str
    trend_items: list[str]
    trend_context: str | None


logger = logging.getLogger(__name__)
settings = get_settings()


class IdeasService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.channel_repository = ChannelRepository(session=session)
        self.generated_content_repository = GeneratedContentRepository(session=session)
        self.openai_ideas_client = OpenAIIdeasClient()
        self.trend_client = TrendClient()

    async def generate_channel_ideas(
        self,
        channel_id: UUID,
        force_refresh: bool = False,
    ) -> GenerateIdeasResponse:
        cached = await self.get_cached_ideas_response(
            channel_id=channel_id,
            force_refresh=force_refresh,
        )
        if cached is not None:
            return cached

        context = await self.build_generation_context(channel_id=channel_id)
        longform = await self.generate_longform_ideas(context=context)
        shortform = await self.generate_shortform_ideas(context=context)
        planner = await self.generate_planner(
            context=context,
            longform=longform.payload,
            shortform=shortform.payload,
        )
        return await self.persist_generated_ideas(
            context=context,
            longform=longform,
            shortform=shortform,
            planner=planner,
        )

    async def get_cached_ideas_response(
        self,
        channel_id: UUID,
        force_refresh: bool = False,
    ) -> GenerateIdeasResponse | None:
        channel = await self.channel_repository.get_by_id(str(channel_id))
        if channel is None:
            raise IdeasGenerationError("Channel not found")

        logger.debug(
            "agent.ideas.start channel_id=%s title=%s force_refresh=%s",
            channel_id,
            channel.title,
            force_refresh,
        )

        if force_refresh:
            return None

        cached = await self.generated_content_repository.get_latest_for_channel(
            channel_id=str(channel_id),
            content_type="content_ideas",
        )
        if cached is None or not cached.result_json:
            return None

        job_id = await create_job(job_namespace="ideas", resource_id=str(channel_id))
        await set_job_status(job_id=job_id, status="completed")
        cached_payload = ContentIdeasPayload.model_validate(cached.result_json)
        logger.debug(
            "agent.ideas.cached channel_id=%s job_id=%s "
            "video_ideas=%s shorts_ideas=%s calendar_items=%s",
            channel_id,
            job_id,
            len(cached_payload.video_ideas),
            len(cached_payload.shorts_ideas),
            len(cached_payload.content_calendar),
        )
        return GenerateIdeasResponse(
            job_id=job_id,
            ideas=self._serialize_ideas(cached),
        )

    async def build_generation_context(self, channel_id: UUID) -> IdeasGenerationContext:
        channel = await self.channel_repository.get_by_id(str(channel_id))
        if channel is None:
            raise IdeasGenerationError("Channel not found")

        analysis_row = await self.generated_content_repository.get_latest_for_channel(
            channel_id=str(channel_id),
            content_type="channel_analysis",
        )
        if analysis_row is None or not analysis_row.result_json:
            raise IdeasGenerationError("Channel analysis not found. Run analysis first.")

        analysis = ChannelAnalysisPayload.model_validate(analysis_row.result_json)
        logger.debug(
            "agent.ideas.analysis_context channel_id=%s analysis_model=%s niche=%s",
            channel_id,
            analysis_row.model_name,
            analysis.niche,
        )

        trend_geo = self._resolve_trend_geo(channel.country)
        trend_items: list[str] = []
        trend_context = None
        if settings.trend_context_enabled:
            try:
                trend_snapshot = self.trend_client.fetch_trending_searches(trend_geo)
                trend_items = trend_snapshot.items
                trend_context = self._build_trend_context(trend_snapshot.items)
                logger.debug(
                    "agent.ideas.trends.loaded channel_id=%s geo=%s source=%s items=%s",
                    channel_id,
                    trend_snapshot.geo,
                    trend_snapshot.source,
                    len(trend_snapshot.items),
                )
            except TrendProviderError:
                logger.exception(
                    "agent.ideas.trends.failed channel_id=%s geo=%s",
                    channel_id,
                    trend_geo,
                )

        return IdeasGenerationContext(
            channel=channel,
            analysis_row=analysis_row,
            analysis=analysis,
            trend_geo=trend_geo,
            trend_items=trend_items,
            trend_context=trend_context,
        )

    async def generate_longform_ideas(
        self,
        context: IdeasGenerationContext,
    ) -> OpenAIParsedResult[LongformIdeasPayload]:
        logger.debug(
            "agent.longform.start channel_id=%s trend_geo=%s trend_loaded=%s",
            context.channel.id,
            context.trend_geo,
            bool(context.trend_items),
        )
        try:
            result = self.openai_ideas_client.generate_longform_ideas(
                channel_title=context.channel.title,
                analysis=context.analysis,
                country_hint=context.trend_geo,
                trend_context=context.trend_context,
            )
        except OpenAIIdeasError as exc:
            logger.exception("agent.longform.failed channel_id=%s", context.channel.id)
            raise IdeasGenerationError(str(exc)) from exc

        logger.debug(
            "agent.longform.completed channel_id=%s model=%s "
            "video_ideas=%s title_hooks=%s thumbnail_angles=%s",
            context.channel.id,
            result.model_name,
            len(result.payload.video_ideas),
            len(result.payload.title_hooks),
            len(result.payload.thumbnail_angles),
        )
        return result

    async def generate_shortform_ideas(
        self,
        context: IdeasGenerationContext,
    ) -> OpenAIParsedResult[ShortformIdeasPayload]:
        logger.debug(
            "agent.shortform.start channel_id=%s trend_geo=%s trend_loaded=%s",
            context.channel.id,
            context.trend_geo,
            bool(context.trend_items),
        )
        try:
            result = self.openai_ideas_client.generate_shortform_ideas(
                channel_title=context.channel.title,
                analysis=context.analysis,
                country_hint=context.trend_geo,
                trend_context=context.trend_context,
            )
        except OpenAIIdeasError as exc:
            logger.exception("agent.shortform.failed channel_id=%s", context.channel.id)
            raise IdeasGenerationError(str(exc)) from exc

        logger.debug(
            "agent.shortform.completed channel_id=%s model=%s shorts_ideas=%s",
            context.channel.id,
            result.model_name,
            len(result.payload.shorts_ideas),
        )
        return result

    async def generate_planner(
        self,
        context: IdeasGenerationContext,
        longform: LongformIdeasPayload,
        shortform: ShortformIdeasPayload,
    ) -> OpenAIParsedResult[PlannerIdeasPayload]:
        logger.debug(
            "agent.planner.start channel_id=%s longform_video_ideas=%s shortform_ideas=%s",
            context.channel.id,
            len(longform.video_ideas),
            len(shortform.shorts_ideas),
        )
        try:
            result = self.openai_ideas_client.generate_planner(
                channel_title=context.channel.title,
                analysis=context.analysis,
                longform=longform,
                shortform=shortform,
                country_hint=context.trend_geo,
            )
        except OpenAIIdeasError as exc:
            logger.exception("agent.planner.failed channel_id=%s", context.channel.id)
            raise IdeasGenerationError(str(exc)) from exc

        logger.debug(
            "agent.planner.completed channel_id=%s model=%s calendar_items=%s",
            context.channel.id,
            result.model_name,
            len(result.payload.content_calendar),
        )
        return result

    async def persist_generated_ideas(
        self,
        *,
        context: IdeasGenerationContext,
        longform: OpenAIParsedResult[LongformIdeasPayload],
        shortform: OpenAIParsedResult[ShortformIdeasPayload],
        planner: OpenAIParsedResult[PlannerIdeasPayload],
    ) -> GenerateIdeasResponse:
        job_id = await create_job(job_namespace="ideas", resource_id=str(context.channel.id))
        await set_job_status(job_id=job_id, status="processing")

        payload = ContentIdeasPayload(
            video_ideas=longform.payload.video_ideas,
            shorts_ideas=shortform.payload.shorts_ideas,
            title_hooks=longform.payload.title_hooks,
            thumbnail_angles=longform.payload.thumbnail_angles,
            content_calendar=planner.payload.content_calendar,
        )
        model_names = sorted({longform.model_name, shortform.model_name, planner.model_name})
        ideas_row = GeneratedContent(
            user_id=context.channel.user_id,
            channel_id=context.channel.id,
            content_type="content_ideas",
            prompt_input={
                "workflow": "langgraph-agentic-v2",
                "agents": ["longform", "shortform", "planner"],
                "analysis_id": context.analysis_row.id,
                "analysis_model": context.analysis_row.model_name,
                "trend_geo": context.trend_geo,
                "trend_loaded": bool(context.trend_items),
                "trend_items": context.trend_items[:5],
                "current_year": datetime.now(UTC).year,
            },
            result_json=payload.model_dump(),
            status="completed",
            model_name="openai:" + ",".join(model_names),
        )
        self.session.add(ideas_row)
        await self.session.commit()
        await self.session.refresh(ideas_row)
        await set_job_status(job_id=job_id, status="completed")
        logger.debug(
            "agent.ideas.completed channel_id=%s job_id=%s model=%s "
            "trend_geo=%s trend_loaded=%s video_ideas=%s shorts_ideas=%s "
            "title_hooks=%s thumbnail_angles=%s calendar_items=%s",
            context.channel.id,
            job_id,
            ideas_row.model_name,
            context.trend_geo,
            bool(context.trend_items),
            len(payload.video_ideas),
            len(payload.shorts_ideas),
            len(payload.title_hooks),
            len(payload.thumbnail_angles),
            len(payload.content_calendar),
        )
        return GenerateIdeasResponse(
            job_id=job_id,
            ideas=self._serialize_ideas(ideas_row),
        )

    async def get_channel_ideas(self, channel_id: UUID) -> ContentIdeasResponse | None:
        record = await self.generated_content_repository.get_latest_for_channel(
            channel_id=str(channel_id),
            content_type="content_ideas",
        )
        if record is None or not record.result_json:
            return None
        return self._serialize_ideas(record)

    @staticmethod
    def _serialize_ideas(record: GeneratedContent) -> ContentIdeasResponse:
        return ContentIdeasResponse(
            id=UUID(record.id),
            channel_id=UUID(record.channel_id),
            content_type=record.content_type,
            status=record.status,
            model_name=record.model_name,
            created_at=record.created_at,
            result=ContentIdeasPayload.model_validate(record.result_json),
        )

    @staticmethod
    def _resolve_trend_geo(country: str | None) -> str:
        if country and len(country.strip()) == 2:
            return country.strip().upper()
        return settings.trend_default_geo

    @staticmethod
    def _build_trend_context(items: list[str]) -> str:
        if not items:
            return "No relevant trend items were available."
        return "\n".join(f"- {item}" for item in items[: settings.trend_max_items])
