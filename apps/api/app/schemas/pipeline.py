from pydantic import BaseModel, HttpUrl

from app.schemas.analysis import ChannelAnalysisResponse
from app.schemas.channel import ChannelSyncResponse
from app.schemas.ideas import ContentIdeasResponse
from app.schemas.transcript import ChannelTranscriptSyncResponse


class RunPipelineRequest(BaseModel):
    channel_url: HttpUrl
    force_transcript_refresh: bool = False
    force_ideas_refresh: bool = True


class RunPipelineResponse(BaseModel):
    job_id: str
    channel_sync: ChannelSyncResponse
    transcript_sync: ChannelTranscriptSyncResponse
    analysis: ChannelAnalysisResponse
    ideas: ContentIdeasResponse
