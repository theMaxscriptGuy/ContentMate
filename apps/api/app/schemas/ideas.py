from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GenerateIdeasRequest(BaseModel):
    force_refresh: bool = False


class PackagingHelp(BaseModel):
    title_options: list[str]
    thumbnail_concept: str
    thumbnail_text: str
    hook_line: str
    packaging_rationale: str


class VideoIdea(BaseModel):
    title: str
    premise: str
    why_it_fits: str
    target_viewer: str
    packaging: PackagingHelp | None = None


class ShortIdea(BaseModel):
    hook: str
    concept: str
    source_moment: str


class TitleHook(BaseModel):
    title: str
    angle: str


class ThumbnailAngle(BaseModel):
    concept: str
    visual_elements: list[str]
    text_overlay: str


class TrendFit(BaseModel):
    trend: str
    relevance: str
    why_it_fits: str
    execution_angle: str


class CalendarItem(BaseModel):
    week: int = Field(ge=1)
    focus: str
    deliverable: str


class LongformIdeasPayload(BaseModel):
    trend_fit: list[TrendFit] = Field(default_factory=list)
    video_ideas: list[VideoIdea]
    title_hooks: list[TitleHook]
    thumbnail_angles: list[ThumbnailAngle]


class ShortformIdeasPayload(BaseModel):
    shorts_ideas: list[ShortIdea]


class PlannerIdeasPayload(BaseModel):
    content_calendar: list[CalendarItem]


class ContentIdeasPayload(BaseModel):
    trend_fit: list[TrendFit] = Field(default_factory=list)
    video_ideas: list[VideoIdea]
    shorts_ideas: list[ShortIdea]
    title_hooks: list[TitleHook]
    thumbnail_angles: list[ThumbnailAngle]
    content_calendar: list[CalendarItem]


class ContentIdeasResponse(BaseModel):
    id: UUID
    channel_id: UUID
    content_type: str
    status: str
    model_name: str | None
    created_at: datetime
    result: ContentIdeasPayload


class GenerateIdeasResponse(BaseModel):
    job_id: str
    ideas: ContentIdeasResponse
