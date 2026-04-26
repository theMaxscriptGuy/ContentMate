from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.analysis import ChannelAnalysisResponse
from app.schemas.channel import ChannelSummary, VideoSummary
from app.schemas.ideas import ContentIdeasResponse


class ChannelHistoryItem(BaseModel):
    channel: ChannelSummary
    analyzed_at: datetime | None
    idea_count: int
    latest_video_title: str | None


class ChannelHistoryResponse(BaseModel):
    channels: list[ChannelHistoryItem]


class SavedChannelResponse(BaseModel):
    channel: ChannelSummary
    videos: list[VideoSummary]
    analysis: ChannelAnalysisResponse | None
    ideas: ContentIdeasResponse | None
    is_stale: bool = False


class SavedChannelListItem(BaseModel):
    id: UUID
    title: str
