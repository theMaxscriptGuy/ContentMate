from datetime import datetime, timezone
from unittest.mock import patch

from app.integrations.youtube.client import (
    YouTubeClient,
    YouTubeVideoPayload,
    _parse_iso8601_duration,
)


def test_extract_channel_reference_from_handle() -> None:
    client = YouTubeClient()
    assert client._extract_channel_reference("https://www.youtube.com/@contentmate") == "@contentmate"


def test_extract_channel_reference_from_channel_id() -> None:
    client = YouTubeClient()
    assert (
        client._extract_channel_reference("https://www.youtube.com/channel/UC123456789")
        == "UC123456789"
    )


def test_parse_iso8601_duration() -> None:
    assert _parse_iso8601_duration("PT1H2M3S") == 3723


def test_select_latest_uploaded_videos_filters_short_videos() -> None:
    client = YouTubeClient()
    published_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    videos = [
        _video("newer-long", published_at, 600),
        _video("older-long", datetime(2020, 1, 1, tzinfo=timezone.utc), 3600),
        _video("too-short", datetime(2026, 2, 1, tzinfo=timezone.utc), 120),
    ]

    selected = client._select_latest_uploaded_videos(videos, max_results=2)

    assert [video.youtube_video_id for video in selected] == ["newer-long", "older-long"]


def test_extract_channel_info_uses_uploads_videos_tab() -> None:
    client = YouTubeClient()

    with patch("app.integrations.youtube.client.yt_dlp.YoutubeDL") as youtube_dl:
        ydl = youtube_dl.return_value.__enter__.return_value
        ydl.extract_info.return_value = {
            "id": "UC123",
            "channel": "Example",
            "entries": [{"id": "video-1", "title": "Video 1", "duration": 600}],
        }

        info = client._extract_channel_info("https://www.youtube.com/@example")

    ydl.extract_info.assert_called_once_with(
        "https://www.youtube.com/@example/videos",
        download=False,
    )
    assert info["entries"] == [{"id": "video-1", "title": "Video 1", "duration": 600}]


def test_fetch_channel_returns_latest_eligible_uploads_without_hydrating() -> None:
    client = YouTubeClient()
    channel_info = {
        "id": "UC123",
        "channel": "Example",
        "entries": [
            {
                "id": "older",
                "title": "Older",
                "duration": 5000,
                "timestamp": 1672531200,
            },
            {
                "id": "newer",
                "title": "Newer",
                "duration": 3000,
                "timestamp": 1704067200,
            },
            {
                "id": "short",
                "title": "Short",
                "duration": 120,
                "timestamp": 1735689600,
            },
        ],
    }

    async def run_test() -> None:
        with patch.object(client, "_extract_channel_info", return_value=channel_info):
            with patch.object(client, "_hydrate_video_payload") as hydrate:
                _, videos = await client.fetch_channel_with_uploaded_videos(
                    "https://www.youtube.com/@example",
                    max_results=2,
                )
        hydrate.assert_not_called()
        assert [video.youtube_video_id for video in videos] == ["newer", "older"]

    import asyncio

    asyncio.run(run_test())


def test_fetch_channel_with_longest_videos_keeps_legacy_latest_upload_behavior() -> None:
    client = YouTubeClient()
    channel_info = {
        "id": "UC123",
        "channel": "Example",
        "entries": [
            {"id": "older-long", "title": "Older", "duration": 5000, "timestamp": 1672531200},
            {"id": "newer-long", "title": "Newer", "duration": 3000, "timestamp": 1704067200},
        ],
    }

    async def run_test() -> None:
        with patch.object(client, "_extract_channel_info", return_value=channel_info):
            _, videos = await client.fetch_channel_with_longest_videos(
                "https://www.youtube.com/@example"
            )
        assert [video.youtube_video_id for video in videos] == ["newer-long"]

    import asyncio

    asyncio.run(run_test())


def _video(
    video_id: str,
    published_at: datetime,
    duration_seconds: int,
) -> YouTubeVideoPayload:
    return YouTubeVideoPayload(
        youtube_video_id=video_id,
        title=video_id,
        description=None,
        published_at=published_at,
        thumbnail_url=None,
        duration_seconds=duration_seconds,
        view_count=None,
        like_count=None,
        comment_count=None,
    )
