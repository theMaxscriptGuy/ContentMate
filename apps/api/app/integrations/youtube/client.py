from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

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

    async def fetch_channel_with_latest_videos(
        self,
        channel_url: str,
        max_results: int = 1,
        include_videos: bool = True,
        include_streams: bool = False,
        include_shorts: bool = False,
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
        include_streams: bool = False,
        include_shorts: bool = False,
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
        include_streams: bool = False,
        include_shorts: bool = False,
    ) -> tuple[YouTubeChannelPayload, list[YouTubeVideoPayload]]:
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
        if include_streams:
            videos = self._hydrate_stream_payloads(videos)
        selected_videos = self._select_latest_uploaded_videos(
            videos=videos,
            max_results=max_results,
        )
        return channel, selected_videos

    async def fetch_video_with_channel(
        self,
        video_url: str,
    ) -> tuple[YouTubeChannelPayload, YouTubeVideoPayload]:
        info = self._extract_video_info(video_url=video_url)
        channel = self._build_channel_payload_from_video_info(info=info)
        video = self._build_video_payload_from_video_info(info=info)
        return channel, video

    def _select_latest_uploaded_videos(
        self,
        videos: list[YouTubeVideoPayload],
        max_results: int = 1,
    ) -> list[YouTubeVideoPayload]:
        return sorted(
            [
                video
                for video in videos
                if video.is_short or (video.duration_seconds or 0) >= self.min_duration_seconds
            ],
            key=lambda video: video.published_at,
            reverse=True,
        )[:max_results]

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
