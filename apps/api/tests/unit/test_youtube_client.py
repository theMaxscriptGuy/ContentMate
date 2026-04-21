from app.integrations.youtube.client import YouTubeClient, _parse_iso8601_duration


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
