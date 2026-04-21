from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.generated_content import GeneratedContent


class GeneratedContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_latest_for_channel(
        self,
        channel_id: str,
        content_type: str,
    ) -> GeneratedContent | None:
        query: Select[tuple[GeneratedContent]] = (
            select(GeneratedContent)
            .where(
                GeneratedContent.channel_id == channel_id,
                GeneratedContent.content_type == content_type,
            )
            .order_by(desc(GeneratedContent.created_at))
        )
        result = await self.session.execute(query)
        return result.scalars().first()
