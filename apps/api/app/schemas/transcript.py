from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TranscriptChunkPreview(BaseModel):
    index: int
    text: str


class TranscriptResponse(BaseModel):
    id: UUID
    video_id: UUID
    language: str | None
    source: str | None
    cleaned_text: str | None
    chunk_count: int | None
    status: str
    error_message: str | None
    fetched_at: datetime | None
    chunks: list[TranscriptChunkPreview]

    model_config = {"from_attributes": True}


class TranscriptRefreshResponse(BaseModel):
    job_id: str
    transcript: TranscriptResponse


class ChannelTranscriptSyncResponse(BaseModel):
    job_id: str
    channel_id: UUID
    processed_videos: int = Field(ge=0)
    fetched_transcripts: int = Field(ge=0)
    failed_transcripts: int = Field(ge=0)
    transcripts: list[TranscriptResponse]
