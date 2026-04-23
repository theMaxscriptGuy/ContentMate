from fastapi import Request

from app.core.rate_limit import get_client_ip


def _build_request(headers: list[tuple[bytes, bytes]], client=None) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/test",
        "headers": headers,
        "client": client,
    }
    return Request(scope)


def test_get_client_ip_prefers_x_forwarded_for() -> None:
    request = _build_request(
        headers=[(b"x-forwarded-for", b"203.0.113.10, 10.0.0.2")],
        client=("127.0.0.1", 1234),
    )

    assert get_client_ip(request) == "203.0.113.10"


def test_get_client_ip_falls_back_to_real_ip_then_client_host() -> None:
    request = _build_request(
        headers=[(b"x-real-ip", b"198.51.100.8")],
        client=("127.0.0.1", 1234),
    )
    assert get_client_ip(request) == "198.51.100.8"

    no_header_request = _build_request(headers=[], client=("127.0.0.1", 1234))
    assert get_client_ip(no_header_request) == "127.0.0.1"
