from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminActivityUser(BaseModel):
    id: UUID
    email: str
    name: str | None


class AdminActivityChannel(BaseModel):
    id: UUID
    title: str
    channel_url: str
    subscriber_count: int | None


class AdminAnalysisActivityItem(BaseModel):
    analysis_id: UUID
    analyzed_at: datetime
    source_kind: str
    analyzed_video_count: int
    analyzed_transcript_count: int
    model_name: str | None
    user: AdminActivityUser
    channel: AdminActivityChannel


class AdminActivitySummary(BaseModel):
    total_users: int
    total_channel_analyses: int
    total_channels: int


class AdminActivityResponse(BaseModel):
    summary: AdminActivitySummary
    activity: list[AdminAnalysisActivityItem]
