from uuid import UUID

from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.channel import Channel
from app.repositories.channel_repository import ChannelRepository
from app.repositories.generated_content_repository import GeneratedContentRepository
from app.schemas.analysis import ChannelAnalysisPayload, ChannelAnalysisResponse
from app.schemas.channel import ChannelSummary, VideoSummary
from app.schemas.history import ChannelHistoryItem, ChannelHistoryResponse, SavedChannelResponse
from app.schemas.ideas import ContentIdeasPayload, ContentIdeasResponse


class HistoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.channel_repository = ChannelRepository(session=session)
        self.generated_content_repository = GeneratedContentRepository(session=session)

    async def list_user_channels(self, user_id: str) -> ChannelHistoryResponse:
        query: Select[tuple[Channel]] = (
            select(Channel)
            .where(Channel.user_id == user_id)
            .order_by(desc(Channel.last_synced_at), desc(Channel.created_at))
        )
        result = await self.session.execute(query)

        items = []
        for channel in result.scalars().all():
            analysis = await self.generated_content_repository.get_latest_for_channel(
                channel_id=channel.id,
                content_type="channel_analysis",
            )
            ideas = await self.generated_content_repository.get_latest_for_channel(
                channel_id=channel.id,
                content_type="content_ideas",
            )
            videos = await self.channel_repository.list_active_videos_for_channel(
                channel_id=channel.id,
                limit=1,
            )
            idea_count = 0
            if ideas and ideas.result_json:
                idea_count = len((ideas.result_json.get("video_ideas") or []))

            items.append(
                ChannelHistoryItem(
                    channel=ChannelSummary.model_validate(channel),
                    analyzed_at=analysis.created_at if analysis else None,
                    idea_count=idea_count,
                    latest_video_title=videos[0].title if videos else None,
                )
            )

        return ChannelHistoryResponse(channels=items)

    async def get_saved_channel(self, user_id: str, channel_id: UUID) -> SavedChannelResponse | None:
        channel = await self.channel_repository.get_by_id(str(channel_id))
        if channel is None or channel.user_id != user_id:
            return None

        videos = await self.channel_repository.list_active_videos_for_channel(channel.id)
        analysis = await self.generated_content_repository.get_latest_for_channel(
            channel_id=channel.id,
            content_type="channel_analysis",
        )
        ideas = await self.generated_content_repository.get_latest_for_channel(
            channel_id=channel.id,
            content_type="content_ideas",
        )

        return SavedChannelResponse(
            channel=ChannelSummary.model_validate(channel),
            videos=[VideoSummary.model_validate(video) for video in videos],
            analysis=_serialize_analysis(analysis) if analysis and analysis.result_json else None,
            ideas=_serialize_ideas(ideas) if ideas and ideas.result_json else None,
        )


def _serialize_analysis(record) -> ChannelAnalysisResponse:
    return ChannelAnalysisResponse(
        id=UUID(record.id),
        channel_id=UUID(record.channel_id),
        content_type=record.content_type,
        status=record.status,
        model_name=record.model_name,
        created_at=record.created_at,
        result=ChannelAnalysisPayload.model_validate(record.result_json),
    )


def _serialize_ideas(record) -> ContentIdeasResponse:
    return ContentIdeasResponse(
        id=UUID(record.id),
        channel_id=UUID(record.channel_id),
        content_type=record.content_type,
        status=record.status,
        model_name=record.model_name,
        created_at=record.created_at,
        result=ContentIdeasPayload.model_validate(record.result_json),
    )
