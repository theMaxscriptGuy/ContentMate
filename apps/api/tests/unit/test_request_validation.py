import pytest
from pydantic import ValidationError

from app.schemas.auth import GoogleLoginRequest
from app.schemas.pipeline import RunPipelineRequest, RunVideoPipelineRequest


@pytest.mark.parametrize(
    "channel_url",
    [
        "https://www.youtube.com/@contentmate",
        "https://youtube.com/channel/UC123456789",
        "https://www.youtube.com/c/example",
        "https://www.youtube.com/user/example",
        "https://www.youtube.com/?channel_id=UC123456789",
    ],
)
def test_pipeline_request_accepts_supported_youtube_channel_urls(channel_url: str) -> None:
    payload = RunPipelineRequest(channel_url=channel_url)

    assert str(payload.channel_url).startswith("https://")


@pytest.mark.parametrize(
    "channel_url",
    [
        "https://example.com/@contentmate",
        "https://youtu.be/video-id",
        "https://www.youtube.com/watch?v=abc",
        "https://www.youtube.com/playlist?list=abc",
    ],
)
def test_pipeline_request_rejects_non_channel_urls(channel_url: str) -> None:
    with pytest.raises(ValidationError):
        RunPipelineRequest(channel_url=channel_url)


def test_google_login_credential_has_reasonable_length_limits() -> None:
    GoogleLoginRequest(credential="x" * 20)

    with pytest.raises(ValidationError):
        GoogleLoginRequest(credential="short")

    with pytest.raises(ValidationError):
        GoogleLoginRequest(credential="x" * 5001)


def test_pipeline_request_requires_at_least_one_content_type() -> None:
    with pytest.raises(ValidationError):
        RunPipelineRequest(
            channel_url="https://www.youtube.com/@contentmate",
            include_videos=False,
            include_streams=False,
            include_shorts=False,
        )


@pytest.mark.parametrize(
    "video_url",
    [
        "https://www.youtube.com/watch?v=abc123",
        "https://youtube.com/watch?v=abc123",
        "https://youtu.be/abc123",
        "https://www.youtube.com/shorts/abc123",
    ],
)
def test_video_pipeline_request_accepts_supported_youtube_video_urls(video_url: str) -> None:
    payload = RunVideoPipelineRequest(video_url=video_url)

    assert str(payload.video_url).startswith("https://")


@pytest.mark.parametrize(
    "video_url",
    [
        "https://example.com/watch?v=abc123",
        "https://www.youtube.com/@contentmate",
        "https://www.youtube.com/playlist?list=abc",
        "https://www.youtube.com/watch",
    ],
)
def test_video_pipeline_request_rejects_non_video_urls(video_url: str) -> None:
    with pytest.raises(ValidationError):
        RunVideoPipelineRequest(video_url=video_url)
