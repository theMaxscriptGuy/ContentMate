import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.channel import Channel
from app.db.models.video import Video
from app.integrations.youtube.client import (
    YouTubeApiError,
    YouTubeChannelPayload,
    YouTubeClient,
    YouTubeVideoPayload,
)
from app.repositories.channel_repository import ChannelRepository
from app.schemas.channel import ChannelSummary, VideoSummary


class ChannelNotFoundError(Exception):
    pass


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ChannelSyncResult:
    channel: ChannelSummary
    videos: list[VideoSummary]


class YouTubeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ChannelRepository(session=session)
        self.client = YouTubeClient()

    async def sync_channel_from_url(
        self,
        channel_url: str,
        user_id: str | None = None,
        include_videos: bool = True,
        include_streams: bool = True,
        include_shorts: bool = True,
    ) -> ChannelSyncResult:
        logger.debug(
            "youtube.sync.start url=%s user_id=%s include_videos=%s "
            "include_streams=%s include_shorts=%s",
            channel_url,
            user_id,
            include_videos,
            include_streams,
            include_shorts,
        )
        try:
            channel_payload, videos_payload = await self.client.fetch_channel_with_uploaded_videos(
                channel_url=channel_url,
                max_results=self.client.candidate_pool_size,
                include_videos=include_videos,
                include_streams=include_streams,
                include_shorts=include_shorts,
            )
        except YouTubeApiError as exc:
            raise ChannelNotFoundError(str(exc)) from exc

        channel = await self._upsert_channel(channel_payload, user_id=user_id)
        videos = await self._upsert_videos(channel_id=channel.id, videos_payload=videos_payload)
        await self.session.commit()
        await self.session.refresh(channel)
        logger.debug(
            "youtube.sync.completed channel_id=%s youtube_channel_id=%s videos=%s",
            channel.id,
            channel.youtube_channel_id,
            len(videos),
        )
        return ChannelSyncResult(
            channel=ChannelSummary.model_validate(channel),
            videos=[VideoSummary.model_validate(video) for video in videos],
        )

    async def refresh_channel(self, channel_id: UUID) -> ChannelSyncResult | None:
        channel = await self.repository.get_by_id(str(channel_id))
        if channel is None:
            return None
        return await self.sync_channel_from_url(channel.channel_url, user_id=channel.user_id)

    async def sync_video_from_url(
        self,
        video_url: str,
        user_id: str | None = None,
    ) -> ChannelSyncResult:
        logger.debug("youtube.video_sync.start url=%s user_id=%s", video_url, user_id)
        try:
            channel_payload, video_payload = await self.client.fetch_video_with_channel(video_url)
        except YouTubeApiError as exc:
            raise ChannelNotFoundError(str(exc)) from exc

        channel = await self._upsert_channel(channel_payload, user_id=user_id)
        videos = await self._upsert_videos(channel_id=channel.id, videos_payload=[video_payload])
        await self.session.commit()
        await self.session.refresh(channel)
        logger.debug(
            "youtube.video_sync.completed channel_id=%s youtube_channel_id=%s video_id=%s",
            channel.id,
            channel.youtube_channel_id,
            video_payload.youtube_video_id,
        )
        return ChannelSyncResult(
            channel=ChannelSummary.model_validate(channel),
            videos=[VideoSummary.model_validate(video) for video in videos],
        )

    async def get_channel_with_videos(
        self, channel_id: UUID
    ) -> tuple[ChannelSummary | None, list[VideoSummary]]:
        channel = await self.repository.get_by_id(str(channel_id))
        if channel is None:
            return None, []
        videos = await self.repository.list_active_videos_for_channel(str(channel_id))
        return (
            ChannelSummary.model_validate(channel),
            [VideoSummary.model_validate(video) for video in videos],
        )

    async def _upsert_channel(
        self,
        payload: YouTubeChannelPayload,
        user_id: str | None = None,
    ) -> Channel:
        channel = await self.repository.get_by_youtube_id(
            payload.youtube_channel_id,
            user_id=user_id,
        )
        if channel is None:
            channel = Channel(
                user_id=user_id,
                youtube_channel_id=payload.youtube_channel_id,
                channel_url=payload.channel_url,
                title=payload.title,
                description=payload.description,
                country=payload.country,
                default_language=payload.default_language,
                subscriber_count=payload.subscriber_count,
                video_count=payload.video_count,
                thumbnail_url=payload.thumbnail_url,
                analysis_status="pending",
                last_synced_at=datetime.now(UTC),
            )
            self.session.add(channel)
            await self.session.flush()
            return channel

        channel.user_id = user_id
        channel.channel_url = payload.channel_url
        channel.title = payload.title
        channel.description = payload.description
        channel.country = payload.country
        channel.default_language = payload.default_language
        channel.subscriber_count = payload.subscriber_count
        channel.video_count = payload.video_count
        channel.thumbnail_url = payload.thumbnail_url
        channel.last_synced_at = datetime.now(UTC)
        await self.session.flush()
        return channel

    async def _upsert_videos(
        self, channel_id: str, videos_payload: list[YouTubeVideoPayload]
    ) -> list[Video]:
        existing_videos = {
            video.youtube_video_id: video
            for video in await self.repository.list_videos_for_channel(channel_id)
        }
        persisted: list[Video] = []

        for payload in videos_payload:
            video = existing_videos.get(payload.youtube_video_id)
            if video is None:
                video = Video(
                    channel_id=channel_id,
                    youtube_video_id=payload.youtube_video_id,
                    title=payload.title,
                    description=payload.description,
                    published_at=payload.published_at,
                    duration_seconds=payload.duration_seconds,
                    view_count=payload.view_count,
                    like_count=payload.like_count,
                    comment_count=payload.comment_count,
                    thumbnail_url=payload.thumbnail_url,
                    transcript_status="pending",
                    analysis_status="pending",
                )
                self.session.add(video)
            else:
                video.title = payload.title
                video.description = payload.description
                video.published_at = payload.published_at
                video.duration_seconds = payload.duration_seconds
                video.view_count = payload.view_count
                video.like_count = payload.like_count
                video.comment_count = payload.comment_count
                video.thumbnail_url = payload.thumbnail_url

            persisted.append(video)

        await self.session.flush()
        return sorted(
            persisted,
            key=lambda video: (
                video.view_count or 0,
                video.like_count or 0,
                video.comment_count or 0,
                video.published_at,
            ),
            reverse=True,
        )
