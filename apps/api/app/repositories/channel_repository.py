from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.channel import Channel
from app.db.models.video import Video


class ChannelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, channel_id: str) -> Channel | None:
        return await self.session.get(Channel, channel_id)

    async def get_by_youtube_id(self, youtube_channel_id: str) -> Channel | None:
        query: Select[tuple[Channel]] = select(Channel).where(
            Channel.youtube_channel_id == youtube_channel_id
        )
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
