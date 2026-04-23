from urllib.parse import urlparse

from pydantic import HttpUrl

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}


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
