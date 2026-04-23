import pytest
from pydantic import ValidationError

from app.schemas.auth import GoogleLoginRequest
from app.schemas.pipeline import RunPipelineRequest


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
