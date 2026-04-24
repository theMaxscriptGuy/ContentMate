from urllib.parse import parse_qs, urlparse

from pydantic import HttpUrl

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}

YOUTUBE_VIDEO_HOSTS = YOUTUBE_HOSTS | {"youtu.be"}


def validate_youtube_channel_url(value: HttpUrl) -> HttpUrl:
    parsed = urlparse(str(value))
    hostname = parsed.hostname or ""
    path = parsed.path.strip("/")

    if hostname.lower() not in YOUTUBE_HOSTS:
        raise ValueError("Only YouTube channel URLs are supported.")

    if path.startswith("@"):
        return value
    if path.startswith(("channel/", "c/", "user/")):
        return value

    query = parsed.query
    if "channel_id=" in query:
        return value

    raise ValueError(
        "Use a YouTube channel URL, for example https://www.youtube.com/@channel."
    )


def validate_youtube_video_url(value: HttpUrl) -> HttpUrl:
    parsed = urlparse(str(value))
    hostname = (parsed.hostname or "").lower()
    path = parsed.path.strip("/")

    if hostname not in YOUTUBE_VIDEO_HOSTS:
        raise ValueError("Only YouTube video URLs are supported.")

    if hostname == "youtu.be" and path:
        return value

    query = parse_qs(parsed.query)
    if path == "watch" and query.get("v"):
        return value

    if path.startswith("shorts/"):
        video_id = path.split("/", maxsplit=1)[1]
        if video_id:
            return value

    raise ValueError(
        "Use a YouTube video URL, for example https://www.youtube.com/watch?v=VIDEO_ID."
    )
