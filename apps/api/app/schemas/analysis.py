from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RunChannelAnalysisRequest(BaseModel):
    fetch_missing_transcripts: bool = True
    force_transcript_refresh: bool = False


class TopicInsight(BaseModel):
    topic: str
    mentions: int


class CreatorProfile(BaseModel):
    creator_archetype: str
    content_style: str
    tone_profile: str
    audience_profile: str
    packaging_style: str
    growth_direction: str


class ChannelAnalysisPayload(BaseModel):
    niche: str
    creator_profile: CreatorProfile | None = None
    primary_topics: list[TopicInsight]
    secondary_topics: list[TopicInsight]
    tone: str
    target_audience: str
    content_patterns: list[str]
    strengths: list[str]
    gaps: list[str]
    transcript_coverage_ratio: float
    analyzed_video_count: int
    analyzed_transcript_count: int


class ChannelAnalysisResponse(BaseModel):
    id: UUID
    channel_id: UUID
    content_type: str
    status: str
    model_name: str | None
    created_at: datetime
    result: ChannelAnalysisPayload


class RunChannelAnalysisResponse(BaseModel):
    job_id: str
    analysis: ChannelAnalysisResponse
    fetched_transcripts: int = Field(ge=0)
    failed_transcripts: int = Field(ge=0)
