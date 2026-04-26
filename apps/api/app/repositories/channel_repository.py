from sqlalchemy import Select, case, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.channel import Channel
from app.db.models.video import Video

settings = get_settings()


class ChannelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, channel_id: str) -> Channel | None:
        return await self.session.get(Channel, channel_id)

    async def get_by_youtube_id(
        self,
        youtube_channel_id: str,
        user_id: str | None = None,
    ) -> Channel | None:
        query: Select[tuple[Channel]] = select(Channel).where(
            Channel.youtube_channel_id == youtube_channel_id
        )
        if user_id is not None:
            query = query.where(Channel.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_videos_for_channel(self, channel_id: str) -> list[Video]:
        query: Select[tuple[Video]] = (
            select(Video)
            .where(Video.channel_id == channel_id)
            .order_by(desc(Video.published_at))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_active_videos_for_channel(
        self,
        channel_id: str,
        limit: int | None = None,
    ) -> list[Video]:
        active_limit = limit or settings.youtube_candidate_pool_size or 1
        query: Select[tuple[Video]] = (
            select(Video)
            .where(
                Video.channel_id == channel_id,
            )
            .order_by(
                case((Video.transcript_status == "failed", 1), else_=0),
                desc(Video.view_count),
                desc(Video.like_count),
                desc(Video.comment_count),
                desc(Video.published_at),
            )
            .limit(active_limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
