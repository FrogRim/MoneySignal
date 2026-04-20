from __future__ import annotations

from collections import deque

import pytest
from fastapi import Request

from app import main as main_module
from app.config import BrainSettings


@pytest.fixture(autouse=True)
def clear_rate_limit_buckets() -> None:
    main_module._RATE_LIMIT_BUCKETS.clear()
    yield
    main_module._RATE_LIMIT_BUCKETS.clear()


def build_request(
    *,
    client_host: str,
    forwarded_for: str | None = None,
    host: str | None = None,
    method: str = "POST",
    path: str = "/v1/signals/evaluate",
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    if host is not None:
        headers.append((b"host", host.encode()))

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "client": (client_host, 1234),
        "server": ("testserver", 80),
    }
    return Request(scope)


def build_rate_limit_settings(
    *,
    trust_forwarded_for: bool = False,
    trusted_proxy_clients: tuple[str, ...] = (),
) -> BrainSettings:
    return BrainSettings(
        rate_limit_enabled=True,
        rate_limit_trust_x_forwarded_for=trust_forwarded_for,
        rate_limit_trusted_proxy_clients=trusted_proxy_clients,
        rate_limit_window_seconds=60,
        rate_limit_max_requests=1,
    )


def test_rate_limit_uses_socket_client_by_default_even_with_forwarded_header() -> None:
    settings = build_rate_limit_settings()
    first_request = build_request(
        client_host="10.0.0.8",
        forwarded_for="198.51.100.1",
    )
    second_request = build_request(
        client_host="10.0.0.8",
        forwarded_for="198.51.100.2",
    )

    first_limited = main_module._enforce_rate_limit(first_request, settings)
    second_limited = main_module._enforce_rate_limit(second_request, settings)

    assert first_limited is False
    assert second_limited is True


def test_rate_limit_prunes_stale_buckets_for_other_clients(monkeypatch) -> None:
    settings = build_rate_limit_settings()
    stale_bucket_key = ("POST", "/v1/signals/evaluate", "stale-client")
    main_module._RATE_LIMIT_BUCKETS[stale_bucket_key] = deque([10.0])
    fresh_request = build_request(client_host="10.0.0.9")

    monkeypatch.setattr(main_module.time, "monotonic", lambda: 100.0)

    limited = main_module._enforce_rate_limit(fresh_request, settings)

    assert limited is False
    assert stale_bucket_key not in main_module._RATE_LIMIT_BUCKETS


def test_rate_limit_ignores_forwarded_header_from_untrusted_client_even_when_enabled(
) -> None:
    settings = build_rate_limit_settings(trust_forwarded_for=True)
    first_request = build_request(
        client_host="10.0.0.8",
        forwarded_for="198.51.100.1",
    )
    second_request = build_request(
        client_host="10.0.0.8",
        forwarded_for="198.51.100.2",
    )

    first_limited = main_module._enforce_rate_limit(first_request, settings)
    second_limited = main_module._enforce_rate_limit(second_request, settings)

    assert first_limited is False
    assert second_limited is True


def test_rate_limit_can_trust_forwarded_header_for_trusted_proxy_client() -> None:
    settings = build_rate_limit_settings(
        trust_forwarded_for=True,
        trusted_proxy_clients=("10.0.0.8",),
    )
    first_request = build_request(
        client_host="10.0.0.8",
        forwarded_for="198.51.100.1",
    )
    second_request = build_request(
        client_host="10.0.0.8",
        forwarded_for="198.51.100.2",
    )

    first_limited = main_module._enforce_rate_limit(first_request, settings)
    second_limited = main_module._enforce_rate_limit(second_request, settings)

    assert first_limited is False
    assert second_limited is False


def test_get_request_host_preserves_ipv6_literal_without_port() -> None:
    request = build_request(
        client_host="10.0.0.8",
        host="[2001:db8::1]:8000",
        method="GET",
        path="/health",
    )

    assert main_module._get_request_host(request) == "2001:db8::1"
