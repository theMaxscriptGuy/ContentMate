from datetime import datetime

from pydantic import BaseModel, Field


class AgentVideoEvidence(BaseModel):
    video_id: str
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


class AgentTranscriptEvidence(BaseModel):
    video_id: str
    status: str
    language: str | None
    source: str | None
    chunk_count: int | None
    error_message: str | None
    cleaned_text: str | None


class AgentWorkflowMeta(BaseModel):
    platform: str = "youtube"
    analysis_mode: str
    transcript_coverage_ratio: float = Field(ge=0, le=1)
    analyzed_video_count: int = Field(ge=0)
    analyzed_transcript_count: int = Field(ge=0)
    selected_content_types: list[str]


class AgentEvidencePackage(BaseModel):
    channel_id: str
    channel_title: str
    channel_description: str | None
    workflow_meta: AgentWorkflowMeta
    videos: list[AgentVideoEvidence]
    transcripts: list[AgentTranscriptEvidence]
    joined_transcript_text: str
