from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.transcript import Transcript
from app.db.models.video import Video


class TranscriptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_video(self, video_id: str) -> Video | None:
        return await self.session.get(Video, video_id)

    async def get_transcript_by_video_id(self, video_id: str) -> Transcript | None:
        query: Select[tuple[Transcript]] = select(Transcript).where(Transcript.video_id == video_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
