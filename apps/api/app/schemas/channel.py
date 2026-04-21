from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ChannelAnalysisRequest(BaseModel):
    channel_url: HttpUrl


class ChannelSummary(BaseModel):
    id: UUID
    youtube_channel_id: str
    channel_url: str
    title: str
    description: str | None
    country: str | None
    default_language: str | None
    subscriber_count: int | None
    video_count: int | None
    thumbnail_url: str | None
    analysis_status: str
    last_synced_at: datetime | None

    model_config = {"from_attributes": True}


class VideoSummary(BaseModel):
    id: UUID
    youtube_video_id: str
    title: str
    description: str | None
    published_at: datetime
    duration_seconds: int | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    thumbnail_url: str | None
    transcript_status: str
    analysis_status: str

    model_config = {"from_attributes": True}


class ChannelDetailResponse(BaseModel):
    channel: ChannelSummary
    videos: list[VideoSummary]


class ChannelSyncResponse(ChannelDetailResponse):
    job_id: str = Field(description="Queue job id for follow-up transcript processing")
