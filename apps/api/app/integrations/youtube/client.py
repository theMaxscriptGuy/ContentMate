import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

import httpx
import yt_dlp

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
    is_short: bool = False
    is_stream: bool = False


class YouTubeClient:
    def __init__(self) -> None:
        self.timeout = settings.request_timeout_seconds
        self.min_duration_seconds = settings.youtube_min_duration_seconds
        self.scan_limit = settings.youtube_scan_limit
        self.candidate_pool_size = settings.youtube_candidate_pool_size
        self.youtube_api_key = settings.youtube_api_key
        self.youtube_api_base_url = settings.youtube_api_base_url.rstrip("/")

    async def fetch_channel_with_latest_videos(
        self,
        channel_url: str,
        max_results: int = 1,
        include_videos: bool = True,
        include_streams: bool = True,
        include_shorts: bool = True,
    ) -> tuple[YouTubeChannelPayload, list[YouTubeVideoPayload]]:
        return await self.fetch_channel_with_uploaded_videos(
            channel_url=channel_url,
            max_results=max_results,
            include_videos=include_videos,
            include_streams=include_streams,
            include_shorts=include_shorts,
        )

    async def fetch_channel_with_longest_videos(
        self,
        channel_url: str,
        max_results: int = 1,
        include_videos: bool = True,
        include_streams: bool = True,
        include_shorts: bool = True,
    ) -> tuple[YouTubeChannelPayload, list[YouTubeVideoPayload]]:
        return await self.fetch_channel_with_uploaded_videos(
            channel_url=channel_url,
            max_results=max_results,
            include_videos=include_videos,
            include_streams=include_streams,
            include_shorts=include_shorts,
        )

    async def fetch_channel_with_uploaded_videos(
        self,
        channel_url: str,
        max_results: int = 1,
        include_videos: bool = True,
        include_streams: bool = True,
        include_shorts: bool = True,
    ) -> tuple[YouTubeChannelPayload, list[YouTubeVideoPayload]]:
        primary_errors: list[str] = []

        if self.youtube_api_key:
            try:
                return await self._fetch_channel_with_official_api(
                    channel_url=channel_url,
                    max_results=max_results,
                    include_videos=include_videos,
                    include_streams=include_streams,
                    include_shorts=include_shorts,
                )
            except Exception as exc:
                primary_errors.append(str(exc))

        info = self._extract_channel_info(
            channel_url=channel_url,
            include_videos=include_videos,
            include_streams=include_streams,
            include_shorts=include_shorts,
        )
        channel = self._build_channel_payload(info=info, channel_url=channel_url)
        videos = self._build_video_payloads(
            info=info,
            include_videos=include_videos,
            include_streams=include_streams,
            include_shorts=include_shorts,
        )
        videos = self._hydrate_video_payloads(videos)
        if include_streams:
            videos = self._hydrate_stream_payloads(videos)
        selected_videos = self._select_segmented_top_videos(
            videos=videos,
            max_results=max_results,
        )
        if not selected_videos and primary_errors:
            raise YouTubeApiError(" | ".join(primary_errors))
        return channel, selected_videos

    async def fetch_video_with_channel(
        self,
        video_url: str,
    ) -> tuple[YouTubeChannelPayload, YouTubeVideoPayload]:
        try:
            info = self._extract_video_info(video_url=video_url)
        except YouTubeApiError:
            return self._build_video_payloads_from_oembed(video_url)

        channel = self._build_channel_payload_from_video_info(info=info)
        video = self._build_video_payload_from_video_info(info=info)
        return channel, video

    async def _fetch_channel_with_official_api(
        self,
        channel_url: str,
        max_results: int,
        include_videos: bool,
        include_streams: bool,
        include_shorts: bool,
    ) -> tuple[YouTubeChannelPayload, list[YouTubeVideoPayload]]:
        channel_reference = self._extract_channel_reference(channel_url)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            channel_info = await self._fetch_channel_metadata_from_api(client, channel_reference)
            channel = self._build_channel_payload_from_api(
                channel_info=channel_info,
                channel_url=channel_url,
            )
            uploads_playlist_id = (
                ((channel_info.get("contentDetails") or {}).get("relatedPlaylists") or {}).get(
                    "uploads"
                )
            )
            if not uploads_playlist_id:
                raise YouTubeApiError("YouTube API did not return the channel uploads playlist.")

            candidate_limit = self.scan_limit if self.scan_limit > 0 else None
            playlist_items = await self._fetch_upload_playlist_items_from_api(
                client=client,
                uploads_playlist_id=uploads_playlist_id,
                max_items=candidate_limit,
            )
            video_ids = [
                item.get("contentDetails", {}).get("videoId")
                for item in playlist_items
                if item.get("contentDetails", {}).get("videoId")
            ]
            if not video_ids:
                raise YouTubeApiError("YouTube API returned no channel videos.")

            video_items = await self._fetch_video_details_from_api(client, video_ids)
            videos = self._build_video_payloads_from_api_items(
                video_items=video_items,
                include_videos=include_videos,
                include_streams=include_streams,
                include_shorts=include_shorts,
            )
            selected_videos = self._select_segmented_top_videos(
                videos=videos,
                max_results=max_results,
            )
            return channel, selected_videos

    def _select_segmented_top_videos(
        self,
        videos: list[YouTubeVideoPayload],
        max_results: int = 1,
    ) -> list[YouTubeVideoPayload]:
        if max_results <= 0:
            return []

        bucket_size = max_results // 3 if max_results >= 3 else 1
        top_videos = sorted(
            [video for video in videos if not video.is_short and not video.is_stream],
            key=lambda video: (
                video.like_count or 0,
                video.view_count or 0,
                video.comment_count or 0,
                video.published_at,
            ),
            reverse=True,
        )[:bucket_size]
        top_shorts = sorted(
            [video for video in videos if video.is_short],
            key=lambda video: (
                video.view_count or 0,
                video.like_count or 0,
                video.comment_count or 0,
                video.published_at,
            ),
            reverse=True,
        )[:bucket_size]
        top_streams = sorted(
            [video for video in videos if video.is_stream],
            key=lambda video: (
                video.view_count or 0,
                video.like_count or 0,
                video.comment_count or 0,
                video.published_at,
            ),
            reverse=True,
        )[:bucket_size]

        combined = top_videos + top_shorts + top_streams
        if len(combined) >= max_results:
            return combined[:max_results]

        selected_ids = {video.youtube_video_id for video in combined}
        remaining = sorted(
            [video for video in videos if video.youtube_video_id not in selected_ids],
            key=lambda video: (
                video.view_count or 0,
                video.like_count or 0,
                video.comment_count or 0,
                video.published_at,
            ),
            reverse=True,
        )
        return (combined + remaining)[:max_results]

    async def _fetch_channel_metadata_from_api(
        self,
        client: httpx.AsyncClient,
        channel_reference: str,
    ) -> dict[str, Any]:
        params = {
            "part": "snippet,statistics,contentDetails",
            "key": self.youtube_api_key,
        }
        if channel_reference.startswith("@"):
            params["forHandle"] = channel_reference.removeprefix("@")
        elif channel_reference.startswith("UC"):
            params["id"] = channel_reference
        else:
            params["forUsername"] = channel_reference

        response = await client.get(f"{self.youtube_api_base_url}/channels", params=params)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items") or []
        if not items:
            raise YouTubeApiError("YouTube API could not resolve the channel.")
        return items[0]

    async def _fetch_upload_playlist_items_from_api(
        self,
        client: httpx.AsyncClient,
        uploads_playlist_id: str,
        max_items: int | None,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token: str | None = None

        while True:
            batch_size = 50
            if max_items is not None:
                remaining = max_items - len(items)
                if remaining <= 0:
                    break
                batch_size = min(batch_size, remaining)

            params = {
                "part": "snippet,contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": batch_size,
                "key": self.youtube_api_key,
            }
            if page_token:
                params["pageToken"] = page_token

            response = await client.get(
                f"{self.youtube_api_base_url}/playlistItems",
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
            batch = payload.get("items") or []
            items.extend(batch)

            page_token = payload.get("nextPageToken")
            if not page_token or not batch:
                break

        return items

    async def _fetch_video_details_from_api(
        self,
        client: httpx.AsyncClient,
        video_ids: list[str],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for chunk in _chunked(video_ids, 50):
            response = await client.get(
                f"{self.youtube_api_base_url}/videos",
                params={
                    "part": "snippet,contentDetails,statistics,liveStreamingDetails",
                    "id": ",".join(chunk),
                    "maxResults": len(chunk),
                    "key": self.youtube_api_key,
                },
            )
            response.raise_for_status()
            items.extend(response.json().get("items") or [])
        return items

    def _build_channel_payload_from_api(
        self,
        channel_info: dict[str, Any],
        channel_url: str,
    ) -> YouTubeChannelPayload:
        snippet = channel_info.get("snippet") or {}
        statistics = channel_info.get("statistics") or {}
        thumbnails = snippet.get("thumbnails") or {}
        thumbnail = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )
        return YouTubeChannelPayload(
            youtube_channel_id=channel_info.get("id") or "",
            channel_url=channel_url,
            title=snippet.get("title") or "Unknown Channel",
            description=snippet.get("description"),
            country=snippet.get("country"),
            default_language=snippet.get("defaultLanguage"),
            subscriber_count=_safe_int(statistics.get("subscriberCount")),
            video_count=_safe_int(statistics.get("videoCount")),
            thumbnail_url=thumbnail,
        )

    def _build_video_payloads_from_api_items(
        self,
        video_items: list[dict[str, Any]],
        include_videos: bool,
        include_streams: bool,
        include_shorts: bool,
    ) -> list[YouTubeVideoPayload]:
        videos: list[YouTubeVideoPayload] = []
        for item in video_items:
            payload = self._build_video_payload_from_api_item(item)
            if payload.is_stream and not include_streams:
                continue
            if payload.is_short and not include_shorts:
                continue
            if not payload.is_stream and not payload.is_short and not include_videos:
                continue
            videos.append(payload)
        return videos

    def _build_video_payload_from_api_item(self, item: dict[str, Any]) -> YouTubeVideoPayload:
        snippet = item.get("snippet") or {}
        statistics = item.get("statistics") or {}
        content_details = item.get("contentDetails") or {}
        live_streaming_details = item.get("liveStreamingDetails") or {}
        thumbnails = snippet.get("thumbnails") or {}
        duration_seconds = _parse_iso8601_duration(content_details.get("duration"))
        live_broadcast_content = str(snippet.get("liveBroadcastContent") or "").lower()
        is_stream = bool(live_streaming_details) or live_broadcast_content in {"live", "upcoming"}
        is_short = not is_stream and duration_seconds is not None and duration_seconds <= 90
        thumbnail = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )

        return YouTubeVideoPayload(
            youtube_video_id=item.get("id") or "",
            title=snippet.get("title") or "Untitled Video",
            description=snippet.get("description"),
            published_at=_parse_api_published_at(snippet.get("publishedAt")),
            thumbnail_url=thumbnail,
            duration_seconds=duration_seconds,
            view_count=_safe_int(statistics.get("viewCount")),
            like_count=_safe_int(statistics.get("likeCount")),
            comment_count=_safe_int(statistics.get("commentCount")),
            is_short=is_short,
            is_stream=is_stream,
        )

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

    def _extract_channel_info(
        self,
        channel_url: str,
        include_videos: bool,
        include_streams: bool,
        include_shorts: bool,
    ) -> dict[str, Any]:
        ydl_opts = {
            "extract_flat": "in_playlist",
            "ignoreerrors": True,
            "quiet": True,
            "no_warnings": True,
            "logger": _YtDlpQuietLogger(),
            "skip_download": True,
            "socket_timeout": self.timeout,
        }
        if self.scan_limit > 0:
            ydl_opts["playlistend"] = self.scan_limit

        infos = []
        errors: list[str] = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for uploads_url in self._build_channel_tab_urls(
                channel_url=channel_url,
                include_videos=include_videos,
                include_streams=include_streams,
                include_shorts=include_shorts,
            ):
                try:
                    info = ydl.extract_info(uploads_url, download=False)
                except Exception as exc:
                    errors.append(str(exc))
                else:
                    if info:
                        infos.append(info)

        if not infos:
            detail = " | ".join(errors) if errors else "No upload tabs returned data."
            raise YouTubeApiError(f"yt-dlp could not inspect channel uploads: {detail}")
        primary_info = infos[0]
        primary_info["entries"] = _dedupe_entries(
            entry
            for info in infos
            for entry in (info.get("entries") or [])
        )
        return primary_info

    def _extract_video_info(self, video_url: str) -> dict[str, Any]:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "logger": _YtDlpQuietLogger(),
            "skip_download": True,
            "socket_timeout": self.timeout,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
        except Exception as exc:
            raise YouTubeApiError(f"yt-dlp could not inspect video: {exc}") from exc

        if not info or not info.get("id"):
            raise YouTubeApiError("yt-dlp response did not include a video id.")
        return info

    def _build_video_payloads_from_oembed(
        self,
        video_url: str,
    ) -> tuple[YouTubeChannelPayload, YouTubeVideoPayload]:
        video_id = self._extract_video_reference(video_url)
        oembed = self._fetch_oembed(video_url)

        author_url = str(oembed.get("author_url") or "").strip()
        channel_url = author_url or f"https://www.youtube.com/watch?v={video_id}"
        channel_id = self._extract_channel_fallback_id(author_url, video_id)
        channel_title = (
            str(oembed.get("author_name") or "Unknown Channel").strip() or "Unknown Channel"
        )
        video_title = str(oembed.get("title") or f"YouTube Video {video_id}").strip()
        thumbnail_url = str(oembed.get("thumbnail_url") or "").strip() or None
        is_short = "/shorts/" in video_url.lower()

        channel = YouTubeChannelPayload(
            youtube_channel_id=channel_id,
            channel_url=channel_url,
            title=channel_title,
            description=None,
            country=None,
            default_language=None,
            subscriber_count=None,
            video_count=None,
            thumbnail_url=thumbnail_url,
        )
        video = YouTubeVideoPayload(
            youtube_video_id=video_id,
            title=video_title,
            description=None,
            published_at=datetime.now(UTC),
            thumbnail_url=thumbnail_url,
            duration_seconds=None,
            view_count=None,
            like_count=None,
            comment_count=None,
            is_short=is_short,
            is_stream=False,
        )
        return channel, video

    def _fetch_oembed(self, video_url: str) -> dict[str, Any]:
        oembed_url = f"https://www.youtube.com/oembed?url={video_url}&format=json"
        try:
            with urlopen(oembed_url, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise YouTubeApiError(
                "Could not inspect the video with yt-dlp or fetch lightweight public metadata."
            ) from exc

    def _extract_video_reference(self, video_url: str) -> str:
        parsed = urlparse(video_url)
        hostname = (parsed.hostname or "").lower()
        path = parsed.path.strip("/")

        if hostname == "youtu.be" and path:
            return path.split("/", maxsplit=1)[0]

        if path == "watch":
            query = parse_qs(parsed.query)
            video_id = (query.get("v") or [""])[0].strip()
            if video_id:
                return video_id

        if path.startswith("shorts/"):
            video_id = path.split("/", maxsplit=1)[1].strip()
            if video_id:
                return video_id

        raise YouTubeApiError("Unsupported YouTube video URL format.")

    def _extract_channel_fallback_id(self, author_url: str, video_id: str) -> str:
        if not author_url:
            return f"video-owner:{video_id}"

        parsed = urlparse(author_url)
        path = parsed.path.strip("/")
        if path:
            return path.replace("/", ":")
        return f"video-owner:{video_id}"

    def _normalize_channel_base_url(self, channel_url: str) -> str:
        parsed = urlparse(channel_url)
        if parsed.netloc and "youtube.com" not in parsed.netloc:
            raise YouTubeApiError("Unsupported YouTube channel URL format.")

        base_url = channel_url.rstrip("/")
        for known_tab in ("videos", "streams", "shorts", "live"):
            suffix = f"/{known_tab}"
            if base_url.endswith(suffix):
                base_url = base_url[: -len(suffix)]
                break
        return base_url

    def _build_channel_tab_urls(
        self,
        channel_url: str,
        include_videos: bool,
        include_streams: bool,
        include_shorts: bool,
    ) -> list[str]:
        base_url = self._normalize_channel_base_url(channel_url)
        tab_urls: list[str] = []
        if include_videos:
            tab_urls.append(f"{base_url}/videos")
        if include_streams:
            tab_urls.append(f"{base_url}/streams")
        if include_shorts:
            tab_urls.append(f"{base_url}/shorts")
        if not tab_urls:
            raise YouTubeApiError("Select at least one content type to analyze.")
        return tab_urls

    def _build_channel_payload(
        self,
        info: dict[str, Any],
        channel_url: str,
    ) -> YouTubeChannelPayload:
        thumbnails = info.get("thumbnails") or []
        thumbnail = thumbnails[-1].get("url") if thumbnails else None
        channel_id = info.get("channel_id") or info.get("uploader_id") or info.get("id")

        if not channel_id:
            raise YouTubeApiError("yt-dlp response did not include a channel id.")

        return YouTubeChannelPayload(
            youtube_channel_id=channel_id,
            channel_url=channel_url,
            title=(
                info.get("channel")
                or info.get("uploader")
                or info.get("title")
                or "Unknown Channel"
            ),
            description=info.get("description"),
            country=None,
            default_language=None,
            subscriber_count=_safe_int(info.get("channel_follower_count")),
            video_count=_safe_int(info.get("playlist_count")) or _safe_int(info.get("n_entries")),
            thumbnail_url=thumbnail,
        )

    def _build_channel_payload_from_video_info(
        self,
        info: dict[str, Any],
    ) -> YouTubeChannelPayload:
        channel_id = info.get("channel_id") or info.get("uploader_id")
        if not channel_id:
            raise YouTubeApiError("yt-dlp response did not include a channel id for the video.")

        thumbnails = info.get("channel_thumbnails") or info.get("thumbnails") or []
        thumbnail = thumbnails[-1].get("url") if thumbnails else None
        channel_url = (
            info.get("channel_url")
            or info.get("uploader_url")
            or f"https://www.youtube.com/channel/{channel_id}"
        )

        return YouTubeChannelPayload(
            youtube_channel_id=channel_id,
            channel_url=channel_url,
            title=(
                info.get("channel")
                or info.get("uploader")
                or info.get("channel_id")
                or "Unknown Channel"
            ),
            description=info.get("channel_description"),
            country=None,
            default_language=info.get("language"),
            subscriber_count=_safe_int(info.get("channel_follower_count")),
            video_count=None,
            thumbnail_url=thumbnail,
        )

    def _build_video_payloads(
        self,
        info: dict[str, Any],
        include_videos: bool,
        include_streams: bool,
        include_shorts: bool,
    ) -> list[YouTubeVideoPayload]:
        videos: list[YouTubeVideoPayload] = []
        for entry in info.get("entries") or []:
            if not entry:
                continue
            content_type = _classify_entry_content_type(entry)
            if content_type is None:
                continue
            if content_type == "videos" and not include_videos:
                continue
            if content_type == "streams" and not include_streams:
                continue
            if content_type == "shorts" and not include_shorts:
                continue
            video_id = entry.get("id")
            if not video_id:
                continue

            videos.append(
                YouTubeVideoPayload(
                    youtube_video_id=video_id,
                    title=entry.get("title") or "Untitled Video",
                    description=entry.get("description"),
                    published_at=_parse_upload_date(entry),
                    thumbnail_url=entry.get("thumbnail"),
                    duration_seconds=_safe_int(entry.get("duration")),
                    view_count=_safe_int(entry.get("view_count")),
                    like_count=_safe_int(entry.get("like_count")),
                    comment_count=_safe_int(entry.get("comment_count")),
                    is_short=content_type == "shorts",
                    is_stream=content_type == "streams",
                )
            )

        return videos

    def _build_video_payload_from_video_info(
        self,
        info: dict[str, Any],
    ) -> YouTubeVideoPayload:
        video_id = info.get("id")
        if not video_id:
            raise YouTubeApiError("yt-dlp response did not include a video id.")

        thumbnails = info.get("thumbnails") or []
        thumbnail = thumbnails[-1].get("url") if thumbnails else None
        webpage_url = str(info.get("webpage_url") or "").lower()
        content_type = _classify_entry_content_type(info)

        if content_type is None:
            if "/shorts/" in webpage_url:
                content_type = "shorts"
            elif str(info.get("live_status") or "").lower() in {
                "is_live",
                "post_live",
                "was_live",
                "is_upcoming",
            }:
                content_type = "streams"
            else:
                content_type = "videos"

        return YouTubeVideoPayload(
            youtube_video_id=video_id,
            title=info.get("title") or "Untitled Video",
            description=info.get("description"),
            published_at=_parse_upload_date(info),
            thumbnail_url=thumbnail,
            duration_seconds=_safe_int(info.get("duration")),
            view_count=_safe_int(info.get("view_count")),
            like_count=_safe_int(info.get("like_count")),
            comment_count=_safe_int(info.get("comment_count")),
            is_short=content_type == "shorts",
            is_stream=content_type == "streams",
        )

    def _hydrate_video_payload(self, video: YouTubeVideoPayload) -> YouTubeVideoPayload:
        video_url = f"https://www.youtube.com/watch?v={video.youtube_video_id}"
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "logger": _YtDlpQuietLogger(),
            "skip_download": True,
            "socket_timeout": self.timeout,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
        except Exception:
            return video

        thumbnails = info.get("thumbnails") or []
        thumbnail = thumbnails[-1].get("url") if thumbnails else video.thumbnail_url
        return YouTubeVideoPayload(
            youtube_video_id=video.youtube_video_id,
            title=info.get("title") or video.title,
            description=info.get("description") or video.description,
            published_at=_parse_upload_date(info),
            thumbnail_url=thumbnail,
            duration_seconds=_safe_int(info.get("duration")) or video.duration_seconds,
            view_count=_safe_int(info.get("view_count")) or video.view_count,
            like_count=_safe_int(info.get("like_count")) or video.like_count,
            comment_count=_safe_int(info.get("comment_count")) or video.comment_count,
            is_short=video.is_short,
            is_stream=video.is_stream,
        )

    def _hydrate_stream_payloads(
        self,
        videos: list[YouTubeVideoPayload],
    ) -> list[YouTubeVideoPayload]:
        hydrated: list[YouTubeVideoPayload] = []
        for video in videos:
            if _looks_like_stream(video):
                hydrated.append(self._hydrate_video_payload(video))
            else:
                hydrated.append(video)
        return hydrated

    def _hydrate_video_payloads(
        self,
        videos: list[YouTubeVideoPayload],
    ) -> list[YouTubeVideoPayload]:
        return [self._hydrate_video_payload(video) for video in videos]


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class _YtDlpQuietLogger:
    def debug(self, _: str) -> None:
        pass

    def info(self, _: str) -> None:
        pass

    def warning(self, _: str) -> None:
        pass

    def error(self, _: str) -> None:
        pass


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


def _parse_upload_date(entry: dict[str, Any]) -> datetime:
    timestamp = _safe_int(entry.get("timestamp"))
    if timestamp is not None:
        return datetime.fromtimestamp(timestamp, tz=UTC)

    upload_date = entry.get("upload_date")
    if isinstance(upload_date, str):
        try:
            return datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=UTC)
        except ValueError:
            pass

    release_timestamp = _safe_int(entry.get("release_timestamp"))
    if release_timestamp is not None:
        return datetime.fromtimestamp(release_timestamp, tz=UTC)

    return datetime.now(UTC)


def _parse_api_published_at(value: Any) -> datetime:
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            pass
    return datetime.now(UTC)


def _chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _dedupe_entries(entries) -> list[dict[str, Any]]:
    seen = set()
    deduped = []
    for entry in entries:
        if not entry:
            continue
        video_id = entry.get("id")
        if not video_id or video_id in seen:
            continue
        seen.add(video_id)
        deduped.append(entry)
    return deduped


def _classify_entry_content_type(entry: dict[str, Any]) -> str | None:
    live_status = str(entry.get("live_status") or "").lower()
    if live_status in {"is_live", "post_live", "was_live", "is_upcoming"}:
        return "streams"

    url_candidates = [
        str(entry.get("url") or "").lower(),
        str(entry.get("webpage_url") or "").lower(),
        str(entry.get("original_url") or "").lower(),
    ]
    if any("/shorts/" in value for value in url_candidates):
        return "shorts"

    channel_tab = str(entry.get("channel_url") or "").lower()
    if "/shorts" in channel_tab:
        return "shorts"
    if "/streams" in channel_tab:
        return "streams"

    overlay_style = str(entry.get("overlay_style") or "").lower()
    if overlay_style == "shorts":
        return "shorts"

    return "videos"


def _looks_like_stream(video: YouTubeVideoPayload) -> bool:
    return video.is_stream
