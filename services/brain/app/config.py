from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BRIEFING_THRESHOLD = 0.55
DEFAULT_INSTANT_PUSH_THRESHOLD = 0.80
DEFAULT_SPECIALIST_CONCURRENCY_LIMIT = 4
DEFAULT_PER_AGENT_TIMEOUT_MS = 3000
DEFAULT_PROVIDER_STRATEGY = "stubbed"
DEFAULT_PROVIDER_NAME = "stub"
DEFAULT_SPECIALIST_MODEL_KEY = "stub-specialist-v1"
DEFAULT_EDITOR_MODEL_KEY = "stub-editor-v1"
DEFAULT_FIXTURE_SCOPE = "KR_ONLY"
DEFAULT_REQUEST_ID_HEADER_NAME = "x-request-id"
DEFAULT_CORS_ALLOW_ORIGINS: tuple[str, ...] = ()
DEFAULT_CORS_ALLOW_CREDENTIALS = False
DEFAULT_TRUSTED_HOSTS: tuple[str, ...] = ()
DEFAULT_RATE_LIMIT_ENABLED = False
DEFAULT_RATE_LIMIT_TRUST_X_FORWARDED_FOR = False
DEFAULT_RATE_LIMIT_TRUSTED_PROXY_CLIENTS: tuple[str, ...] = ()
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60
DEFAULT_RATE_LIMIT_MAX_REQUESTS = 60


class ConfigError(ValueError):
    """Raised when an environment-backed config value is invalid."""


def _read_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a float") from exc


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc


def _read_str(name: str, default: str) -> str:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    value = raw_value.strip()
    if not value:
        raise ConfigError(f"{name} must not be empty")

    return value


def _read_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    value = raw_value.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False

    raise ConfigError(f"{name} must be a boolean")


def _read_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    values = tuple(item.strip() for item in raw_value.split(",") if item.strip())
    return values


@dataclass(frozen=True)
class BrainSettings:
    briefing_threshold: float = DEFAULT_BRIEFING_THRESHOLD
    instant_push_threshold: float = DEFAULT_INSTANT_PUSH_THRESHOLD
    specialist_concurrency_limit: int = DEFAULT_SPECIALIST_CONCURRENCY_LIMIT
    per_agent_timeout_ms: int = DEFAULT_PER_AGENT_TIMEOUT_MS
    provider_strategy: str = DEFAULT_PROVIDER_STRATEGY
    default_provider: str = DEFAULT_PROVIDER_NAME
    specialist_model_key: str = DEFAULT_SPECIALIST_MODEL_KEY
    editor_model_key: str = DEFAULT_EDITOR_MODEL_KEY
    fixture_scope: str = DEFAULT_FIXTURE_SCOPE
    request_id_header_name: str = DEFAULT_REQUEST_ID_HEADER_NAME
    cors_allow_origins: tuple[str, ...] = DEFAULT_CORS_ALLOW_ORIGINS
    cors_allow_credentials: bool = DEFAULT_CORS_ALLOW_CREDENTIALS
    trusted_hosts: tuple[str, ...] = DEFAULT_TRUSTED_HOSTS
    rate_limit_enabled: bool = DEFAULT_RATE_LIMIT_ENABLED
    rate_limit_trust_x_forwarded_for: bool = (
        DEFAULT_RATE_LIMIT_TRUST_X_FORWARDED_FOR
    )
    rate_limit_trusted_proxy_clients: tuple[str, ...] = (
        DEFAULT_RATE_LIMIT_TRUSTED_PROXY_CLIENTS
    )
    rate_limit_window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS
    rate_limit_max_requests: int = DEFAULT_RATE_LIMIT_MAX_REQUESTS


def get_settings() -> BrainSettings:
    settings = BrainSettings(
        briefing_threshold=_read_float(
            "BRAIN_BRIEFING_THRESHOLD",
            DEFAULT_BRIEFING_THRESHOLD,
        ),
        instant_push_threshold=_read_float(
            "BRAIN_INSTANT_PUSH_THRESHOLD",
            DEFAULT_INSTANT_PUSH_THRESHOLD,
        ),
        specialist_concurrency_limit=_read_int(
            "BRAIN_SPECIALIST_CONCURRENCY_LIMIT",
            DEFAULT_SPECIALIST_CONCURRENCY_LIMIT,
        ),
        per_agent_timeout_ms=_read_int(
            "BRAIN_PER_AGENT_TIMEOUT_MS",
            DEFAULT_PER_AGENT_TIMEOUT_MS,
        ),
        provider_strategy=_read_str(
            "BRAIN_PROVIDER_STRATEGY",
            DEFAULT_PROVIDER_STRATEGY,
        ),
        default_provider=_read_str(
            "BRAIN_DEFAULT_PROVIDER",
            DEFAULT_PROVIDER_NAME,
        ),
        specialist_model_key=_read_str(
            "BRAIN_SPECIALIST_MODEL_KEY",
            DEFAULT_SPECIALIST_MODEL_KEY,
        ),
        editor_model_key=_read_str(
            "BRAIN_EDITOR_MODEL_KEY",
            DEFAULT_EDITOR_MODEL_KEY,
        ),
        fixture_scope=_read_str(
            "BRAIN_FIXTURE_SCOPE",
            DEFAULT_FIXTURE_SCOPE,
        ),
        request_id_header_name=_read_str(
            "BRAIN_REQUEST_ID_HEADER_NAME",
            DEFAULT_REQUEST_ID_HEADER_NAME,
        ).lower(),
        cors_allow_origins=_read_csv(
            "BRAIN_CORS_ALLOW_ORIGINS",
            DEFAULT_CORS_ALLOW_ORIGINS,
        ),
        cors_allow_credentials=_read_bool(
            "BRAIN_CORS_ALLOW_CREDENTIALS",
            DEFAULT_CORS_ALLOW_CREDENTIALS,
        ),
        trusted_hosts=tuple(
            host.lower()
            for host in _read_csv(
                "BRAIN_TRUSTED_HOSTS",
                DEFAULT_TRUSTED_HOSTS,
            )
        ),
        rate_limit_enabled=_read_bool(
            "BRAIN_RATE_LIMIT_ENABLED",
            DEFAULT_RATE_LIMIT_ENABLED,
        ),
        rate_limit_trust_x_forwarded_for=_read_bool(
            "BRAIN_RATE_LIMIT_TRUST_X_FORWARDED_FOR",
            DEFAULT_RATE_LIMIT_TRUST_X_FORWARDED_FOR,
        ),
        rate_limit_trusted_proxy_clients=tuple(
            client.lower()
            for client in _read_csv(
                "BRAIN_RATE_LIMIT_TRUSTED_PROXY_CLIENTS",
                DEFAULT_RATE_LIMIT_TRUSTED_PROXY_CLIENTS,
            )
        ),
        rate_limit_window_seconds=_read_int(
            "BRAIN_RATE_LIMIT_WINDOW_SECONDS",
            DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
        ),
        rate_limit_max_requests=_read_int(
            "BRAIN_RATE_LIMIT_MAX_REQUESTS",
            DEFAULT_RATE_LIMIT_MAX_REQUESTS,
        ),
    )
    _validate_settings(settings)
    return settings


def _validate_settings(settings: BrainSettings) -> None:
    if not 0.0 <= settings.briefing_threshold <= 1.0:
        raise ConfigError("briefing_threshold must be between 0.0 and 1.0")

    if not 0.0 <= settings.instant_push_threshold <= 1.0:
        raise ConfigError("instant_push_threshold must be between 0.0 and 1.0")

    if settings.instant_push_threshold < settings.briefing_threshold:
        raise ConfigError(
            "instant_push_threshold must be greater than or equal to "
            "briefing_threshold",
        )

    if settings.specialist_concurrency_limit < 1:
        raise ConfigError("specialist_concurrency_limit must be at least 1")

    if settings.per_agent_timeout_ms < 1:
        raise ConfigError("per_agent_timeout_ms must be at least 1")

    if settings.provider_strategy != DEFAULT_PROVIDER_STRATEGY:
        raise ConfigError(
            "provider_strategy must stay 'stubbed' for the v1 foundation slice",
        )

    if settings.fixture_scope != DEFAULT_FIXTURE_SCOPE:
        raise ConfigError(
            "fixture_scope must stay 'KR_ONLY' for the v1 foundation slice",
        )

    if not settings.request_id_header_name:
        raise ConfigError("request_id_header_name must not be empty")

    for origin in settings.cors_allow_origins:
        if not origin.startswith(("http://", "https://")):
            raise ConfigError("cors_allow_origins must use http or https origins")

    if settings.cors_allow_credentials and not settings.cors_allow_origins:
        raise ConfigError(
            "cors_allow_credentials requires at least one allowed origin",
        )

    if settings.rate_limit_window_seconds < 1:
        raise ConfigError("rate_limit_window_seconds must be at least 1")

    if settings.rate_limit_max_requests < 1:
        raise ConfigError("rate_limit_max_requests must be at least 1")
