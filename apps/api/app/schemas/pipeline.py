from pydantic import BaseModel, HttpUrl, field_validator

from app.schemas.analysis import ChannelAnalysisResponse
from app.schemas.channel import ChannelSyncResponse
from app.schemas.ideas import ContentIdeasResponse
from app.schemas.transcript import ChannelTranscriptSyncResponse
from app.schemas.validators import validate_youtube_channel_url, validate_youtube_video_url


class RunPipelineRequest(BaseModel):
    channel_url: HttpUrl
    force_transcript_refresh: bool = False
    force_ideas_refresh: bool = True

    @field_validator("channel_url")
    @classmethod
    def validate_channel_url(cls, value: HttpUrl) -> HttpUrl:
        return validate_youtube_channel_url(value)


class RunVideoPipelineRequest(BaseModel):
    video_url: HttpUrl
    force_transcript_refresh: bool = False
    force_ideas_refresh: bool = True

    @field_validator("video_url")
    @classmethod
    def validate_video_url(cls, value: HttpUrl) -> HttpUrl:
        return validate_youtube_video_url(value)


class RunPipelineResponse(BaseModel):
    job_id: str
    channel_sync: ChannelSyncResponse
    transcript_sync: ChannelTranscriptSyncResponse
    analysis: ChannelAnalysisResponse
    ideas: ContentIdeasResponse
