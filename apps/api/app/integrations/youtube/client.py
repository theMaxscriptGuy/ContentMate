from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from app.core.config import get_settings

settings = get_settings()


class YouTubeApiError(Exception):
    pass


@dataclass(slots=True)
class YouTubeChannelPayload:
    youtube_channel_id: str
    channel_url: str
    title: str
    description: str | None
    country: str | None
    default_language: str | None
    subscriber_count: int | None
    video_count: int | None
    thumbnail_url: str | None


@dataclass(slots=True)
class YouTubeVideoPayload:
    youtube_video_id: str
    title: str
    description: str | None
    published_at: datetime
    thumbnail_url: str | None
    duration_seconds: int | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None


class YouTubeClient:
    def __init__(self) -> None:
        self.base_url = str(settings.youtube_api_base_url)
        self.timeout = settings.request_timeout_seconds
        self.api_key = settings.youtube_api_key

    async def fetch_channel_with_latest_videos(
        self,
        channel_url: str,
        max_results: int = 10,
    ) -> tuple[YouTubeChannelPayload, list[YouTubeVideoPayload]]:
        channel_ref = self._extract_channel_reference(channel_url)
        channel = await self._resolve_channel(channel_ref=channel_ref, channel_url=channel_url)
        uploads_playlist_id = await self._fetch_uploads_playlist_id(channel.youtube_channel_id)
        video_ids = await self._fetch_latest_video_ids(
            uploads_playlist_id=uploads_playlist_id,
            max_results=max_results,
        )
        videos = await self._fetch_video_details(video_ids=video_ids)
        return channel, videos

    def _extract_channel_reference(self, channel_url: str) -> str:
        parsed = urlparse(channel_url)
        path = parsed.path.strip("/")

        if path.startswith("@"):
            return path
        if path.startswith("channel/"):
            return path.split("/", maxsplit=1)[1]
        if path.startswith("c/") or path.startswith("user/"):
            return path.split("/", maxsplit=1)[1]

        query = parse_qs(parsed.query)
        if "channel_id" in query:
            return query["channel_id"][0]

        raise YouTubeApiError("Unsupported YouTube channel URL format.")

    async def _resolve_channel(
        self, channel_ref: str, channel_url: str
    ) -> YouTubeChannelPayload:
        if channel_ref.startswith("UC"):
            payload = await self._request_json(
                "/channels",
                params={
                    "part": "snippet,statistics,brandingSettings",
                    "id": channel_ref,
                    "key": self.api_key,
                },
            )
        elif channel_ref.startswith("@"):
            payload = await self._request_json(
                "/channels",
                params={
                    "part": "snippet,statistics,brandingSettings",
                    "forHandle": channel_ref[1:],
                    "key": self.api_key,
                },
            )
        else:
            payload = await self._request_json(
                "/channels",
                params={
                    "part": "snippet,statistics,brandingSettings",
                    "forUsername": channel_ref,
                    "key": self.api_key,
                },
            )

        items = payload.get("items", [])
        if not items:
            raise YouTubeApiError("Channel not found in YouTube API response.")

        item = items[0]
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        branding = item.get("brandingSettings", {}).get("channel", {})
        thumbnails = snippet.get("thumbnails", {})
        high_thumb = thumbnails.get("high") or thumbnails.get("default") or {}

        return YouTubeChannelPayload(
            youtube_channel_id=item["id"],
            channel_url=channel_url,
            title=snippet.get("title", "Unknown Channel"),
            description=snippet.get("description"),
            country=snippet.get("country"),
            default_language=branding.get("defaultLanguage"),
            subscriber_count=_safe_int(statistics.get("subscriberCount")),
            video_count=_safe_int(statistics.get("videoCount")),
            thumbnail_url=high_thumb.get("url"),
        )

    async def _fetch_uploads_playlist_id(self, youtube_channel_id: str) -> str:
        payload = await self._request_json(
            "/channels",
            params={
                "part": "contentDetails",
                "id": youtube_channel_id,
                "key": self.api_key,
            },
        )
        items = payload.get("items", [])
        if not items:
            raise YouTubeApiError("Upload playlist not found for channel.")
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    async def _fetch_latest_video_ids(self, uploads_playlist_id: str, max_results: int) -> list[str]:
        payload = await self._request_json(
            "/playlistItems",
            params={
                "part": "contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": max_results,
                "key": self.api_key,
            },
        )
        return [
            item["contentDetails"]["videoId"]
            for item in payload.get("items", [])
            if item.get("contentDetails", {}).get("videoId")
        ]

    async def _fetch_video_details(self, video_ids: list[str]) -> list[YouTubeVideoPayload]:
        if not video_ids:
            return []

        payload = await self._request_json(
            "/videos",
            params={
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(video_ids),
                "key": self.api_key,
            },
        )

        items_by_id: dict[str, dict[str, Any]] = {item["id"]: item for item in payload.get("items", [])}
        videos: list[YouTubeVideoPayload] = []

        for video_id in video_ids:
            item = items_by_id.get(video_id)
            if item is None:
                continue

            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            thumbnails = snippet.get("thumbnails", {})
            high_thumb = thumbnails.get("high") or thumbnails.get("default") or {}

            videos.append(
                YouTubeVideoPayload(
                    youtube_video_id=video_id,
                    title=snippet.get("title", "Untitled Video"),
                    description=snippet.get("description"),
                    published_at=datetime.fromisoformat(
                        snippet["publishedAt"].replace("Z", "+00:00")
                    ),
                    thumbnail_url=high_thumb.get("url"),
                    duration_seconds=_parse_iso8601_duration(item.get("contentDetails", {}).get("duration")),
                    view_count=_safe_int(stats.get("viewCount")),
                    like_count=_safe_int(stats.get("likeCount")),
                    comment_count=_safe_int(stats.get("commentCount")),
                )
            )

        return videos

    async def _request_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            response = await client.get(path, params=params)

        if response.status_code >= 400:
            raise YouTubeApiError(f"YouTube API error: {response.status_code} {response.text}")

        return response.json()


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_iso8601_duration(duration: str | None) -> int | None:
    if not duration:
        return None

    value = duration.removeprefix("PT")
    total = 0
    number = ""

    multipliers = {"H": 3600, "M": 60, "S": 1}
    for char in value:
        if char.isdigit():
            number += char
            continue
        if char in multipliers and number:
            total += int(number) * multipliers[char]
            number = ""

    return total or None
