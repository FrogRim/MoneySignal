from __future__ import annotations

import time
from collections import deque
from typing import Any, Awaitable, Callable, TypeVar
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import BrainSettings, get_settings
from app.contracts import CandidateEventRequest, EvaluateSignalSuccessResponse
from app.contracts.errors import ErrorCode, ErrorDetail, ErrorEnvelope
from app.orchestrators.evaluate_signal import AnalysisFailedError, EvaluateSignalService

app = FastAPI(title="MoneySignal Agent Brain")

_RATE_LIMIT_BUCKETS: dict[tuple[str, str, str], deque[float]] = {}
AppResponse = TypeVar("AppResponse", bound=Response)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "model": ErrorEnvelope,
        "description": "Invalid host header.",
    },
    422: {
        "model": ErrorEnvelope,
        "description": "Invalid request payload.",
    },
    429: {
        "model": ErrorEnvelope,
        "description": "Rate limit exceeded.",
    },
    503: {
        "model": ErrorEnvelope,
        "description": (
            "Upstream timeout, upstream unavailability, or analysis failure."
        ),
    },
    500: {
        "model": ErrorEnvelope,
        "description": "Unexpected internal error.",
    },
}


def _build_error_response(
    request: Request,
    *,
    code: ErrorCode,
    message: str,
    retryable: bool,
    failed_agents: list[str] | None = None,
    status_code: int,
) -> JSONResponse:
    error = ErrorDetail(
        code=code,
        message=message,
        retryable=retryable,
        failed_agents=failed_agents or [],
        trace_id=_get_trace_id(request),
    )
    envelope = ErrorEnvelope(error=error)
    response = JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
    )
    settings = get_settings()
    return _apply_security_headers(request, response, settings)


def _get_trace_id(request: Request) -> str:
    trace_id = getattr(request.state, "trace_id", None)
    if isinstance(trace_id, str) and trace_id:
        return trace_id

    trace_id = f"req_{uuid4().hex[:12]}"
    request.state.trace_id = trace_id
    return trace_id


def _is_origin_allowed(origin: str, settings: BrainSettings) -> bool:
    return origin in settings.cors_allow_origins


def _apply_cors_headers(
    request: Request,
    response: Response,
    settings: BrainSettings,
) -> None:
    origin = request.headers.get("origin")
    if origin is None or not _is_origin_allowed(origin, settings):
        return

    response.headers["access-control-allow-origin"] = origin
    response.headers["vary"] = "Origin"
    if settings.cors_allow_credentials:
        response.headers["access-control-allow-credentials"] = "true"

    if request.method == "OPTIONS":
        response.headers["access-control-allow-methods"] = "GET, POST, OPTIONS"
        requested_headers = request.headers.get("access-control-request-headers")
        if requested_headers:
            response.headers["access-control-allow-headers"] = requested_headers
        else:
            response.headers["access-control-allow-headers"] = "content-type"


def _apply_security_headers(
    request: Request,
    response: AppResponse,
    settings: BrainSettings,
) -> AppResponse:
    response.headers[settings.request_id_header_name] = _get_trace_id(request)
    response.headers["x-content-type-options"] = "nosniff"
    response.headers["x-frame-options"] = "DENY"
    response.headers["referrer-policy"] = "no-referrer"
    response.headers["content-security-policy"] = (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )
    _apply_cors_headers(request, response, settings)
    return response


def _get_request_host(request: Request) -> str:
    host = request.headers.get("host", "").strip().lower()
    if host.startswith("["):
        closing_bracket = host.find("]")
        if closing_bracket != -1:
            return host[1:closing_bracket]
        return host.lstrip("[")
    if ":" in host:
        return host.split(":", maxsplit=1)[0]
    return host


def _is_trusted_proxy_client(request: Request, settings: BrainSettings) -> bool:
    if request.client is None:
        return False
    return request.client.host.lower() in settings.rate_limit_trusted_proxy_clients


def _client_identifier(request: Request, settings: BrainSettings) -> str:
    if (
        settings.rate_limit_trust_x_forwarded_for
        and _is_trusted_proxy_client(request, settings)
    ):
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",", maxsplit=1)[0].strip()
            if client_ip:
                return client_ip

    if request.client is not None:
        return request.client.host

    return "unknown"


def _prune_rate_limit_buckets(window_start: float) -> None:
    stale_bucket_keys: list[tuple[str, str, str]] = []
    for bucket_key, bucket in _RATE_LIMIT_BUCKETS.items():
        while bucket and bucket[0] <= window_start:
            bucket.popleft()
        if not bucket:
            stale_bucket_keys.append(bucket_key)

    for bucket_key in stale_bucket_keys:
        _RATE_LIMIT_BUCKETS.pop(bucket_key, None)


def _enforce_rate_limit(request: Request, settings: BrainSettings) -> bool:
    if not settings.rate_limit_enabled:
        return False

    if request.method != "POST" or request.url.path != "/v1/signals/evaluate":
        return False

    now = time.monotonic()
    window_start = now - settings.rate_limit_window_seconds
    _prune_rate_limit_buckets(window_start)

    bucket_key = (
        request.method,
        request.url.path,
        _client_identifier(request, settings),
    )
    bucket = _RATE_LIMIT_BUCKETS.get(bucket_key)
    if bucket is None:
        bucket = deque()
        _RATE_LIMIT_BUCKETS[bucket_key] = bucket

    if len(bucket) >= settings.rate_limit_max_requests:
        return True

    bucket.append(now)
    return False


@app.middleware("http")
async def apply_http_hardening(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    settings = get_settings()
    _get_trace_id(request)

    if settings.trusted_hosts:
        request_host = _get_request_host(request)
        if request_host not in settings.trusted_hosts:
            return _build_error_response(
                request,
                code=ErrorCode.INVALID_REQUEST,
                message="host header is not allowed",
                retryable=False,
                status_code=400,
            )

    if request.method == "OPTIONS":
        return _apply_security_headers(request, Response(status_code=204), settings)

    if _enforce_rate_limit(request, settings):
        return _build_error_response(
            request,
            code=ErrorCode.RATE_LIMITED,
            message="request rate limit exceeded",
            retryable=True,
            status_code=429,
        )

    response = await call_next(request)
    return _apply_security_headers(request, response, settings)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request,
    _exc: RequestValidationError,
) -> JSONResponse:
    return _build_error_response(
        request,
        code=ErrorCode.INVALID_REQUEST,
        message="request payload failed validation",
        retryable=False,
        status_code=422,
    )


@app.exception_handler(AnalysisFailedError)
async def handle_analysis_failed_error(
    request: Request,
    exc: AnalysisFailedError,
) -> JSONResponse:
    return _build_error_response(
        request,
        code=ErrorCode.ANALYSIS_FAILED,
        message=str(exc),
        retryable=True,
        failed_agents=exc.failed_agents,
        status_code=503,
    )


@app.exception_handler(TimeoutError)
async def handle_timeout_error(request: Request, _exc: TimeoutError) -> JSONResponse:
    return _build_error_response(
        request,
        code=ErrorCode.UPSTREAM_TIMEOUT,
        message="upstream evaluation timed out",
        retryable=True,
        status_code=503,
    )


@app.exception_handler(ConnectionError)
async def handle_connection_error(
    request: Request,
    _exc: ConnectionError,
) -> JSONResponse:
    return _build_error_response(
        request,
        code=ErrorCode.UPSTREAM_UNAVAILABLE,
        message="upstream dependency unavailable",
        retryable=True,
        status_code=503,
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, _exc: Exception) -> JSONResponse:
    return _build_error_response(
        request,
        code=ErrorCode.INTERNAL_ERROR,
        message="internal server error",
        retryable=True,
        status_code=500,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/v1/signals/evaluate",
    response_model=EvaluateSignalSuccessResponse,
    responses=ERROR_RESPONSES,
)
async def evaluate_signal(
    candidate_event: CandidateEventRequest,
) -> EvaluateSignalSuccessResponse:
    service = EvaluateSignalService()
    return await service.evaluate(candidate_event)
