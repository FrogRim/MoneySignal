from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contracts.errors import ErrorEnvelope


def build_valid_error_payload() -> dict[str, object]:
    return {
        "error": {
            "code": "analysis_failed",
            "message": "minimum specialist coverage not met",
            "retryable": True,
            "failed_agents": ["flow", "risk"],
            "trace_id": "req_20260416_001",
        },
    }


def test_error_envelope_accepts_structured_error_shape() -> None:
    payload = build_valid_error_payload()

    model = ErrorEnvelope.model_validate(payload)

    assert model.error.code == "analysis_failed"
    assert model.error.retryable is True
    assert model.error.failed_agents == ["flow", "risk"]
    assert model.error.trace_id == "req_20260416_001"


def test_error_envelope_rejects_unsupported_error_code() -> None:
    payload = build_valid_error_payload()
    payload["error"]["code"] = "unknown_error"

    with pytest.raises(ValidationError):
        ErrorEnvelope.model_validate(payload)


def test_error_envelope_requires_trace_id_and_forbids_extra_fields() -> None:
    payload = build_valid_error_payload()
    del payload["error"]["trace_id"]

    with pytest.raises(ValidationError):
        ErrorEnvelope.model_validate(payload)

    payload = build_valid_error_payload()
    payload["error"]["unexpected"] = True

    with pytest.raises(ValidationError):
        ErrorEnvelope.model_validate(payload)
