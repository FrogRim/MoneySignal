from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.contracts import CandidateEventRequest, EvaluateSignalSuccessResponse
from app.contracts.errors import ErrorCode, ErrorDetail, ErrorEnvelope
from app.orchestrators.evaluate_signal import AnalysisFailedError, EvaluateSignalService

app = FastAPI(title="MoneySignal Agent Brain")

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {
        "model": ErrorEnvelope,
        "description": "Invalid request payload.",
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
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(mode="json"),
    )


def _get_trace_id(request: Request) -> str:
    trace_id = getattr(request.state, "trace_id", None)
    if isinstance(trace_id, str) and trace_id:
        return trace_id

    trace_id = f"req_{uuid4().hex[:12]}"
    request.state.trace_id = trace_id
    return trace_id


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
