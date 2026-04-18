from __future__ import annotations

from httpx import ASGITransport, AsyncClient, Response

from app.main import app
from app.orchestrators.evaluate_signal import AnalysisFailedError, EvaluateSignalService


def build_candidate_event_payload() -> dict[str, object]:
    return {
        "candidate_id": "cand_20260416_001",
        "asset": {
            "symbol": "005930",
            "name": "삼성전자",
            "market": "KR",
        },
        "trigger_type": "price_volume_breakout",
        "event_ts": "2026-04-16T09:12:00+09:00",
        "market_snapshot": {
            "price_change_pct": 3.2,
            "volume_ratio": 2.1,
        },
        "news_items": [
            {"id": "news_1", "headline": "headline_1"},
            {"id": "news_2", "headline": "headline_2"},
        ],
        "flow_snapshot": {
            "foreign_net_buy": 1200000000,
        },
        "theme_context": [
            {"theme": "ai"},
            {"theme": "semiconductor"},
        ],
        "metadata": {
            "gate_score": 0.70,
            "event_ref": "evt_123",
            "stub_agent_outputs": {},
        },
    }


async def post_evaluate_signal(
    payload: dict[str, object],
    *,
    raise_app_exceptions: bool = True,
) -> Response:
    transport = ASGITransport(
        app=app,
        raise_app_exceptions=raise_app_exceptions,
    )

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.post("/v1/signals/evaluate", json=payload)


def assert_error_envelope(
    body: dict[str, object],
    *,
    code: str,
    retryable: bool,
    failed_agents: list[str],
) -> None:
    assert set(body) == {"error"}

    error = body["error"]
    assert isinstance(error, dict)
    assert error["code"] == code
    assert error["retryable"] is retryable
    assert error["failed_agents"] == failed_agents
    assert isinstance(error["message"], str)
    assert error["message"]
    assert isinstance(error["trace_id"], str)
    assert error["trace_id"]


async def test_post_evaluate_rejects_invalid_request_with_structured_error() -> None:
    payload = build_candidate_event_payload()
    del payload["candidate_id"]

    response = await post_evaluate_signal(payload)

    assert response.status_code == 422
    assert_error_envelope(
        response.json(),
        code="invalid_request",
        retryable=False,
        failed_agents=[],
    )


async def test_post_evaluate_returns_analysis_failed_error_envelope(
    monkeypatch,
) -> None:
    async def fake_evaluate(
        self: EvaluateSignalService,
        _candidate_event: object,
    ) -> object:
        raise AnalysisFailedError(
            failed_agents=["flow", "risk"],
            message="minimum specialist coverage not met",
        )

    monkeypatch.setattr(EvaluateSignalService, "evaluate", fake_evaluate)

    response = await post_evaluate_signal(build_candidate_event_payload())

    assert response.status_code == 503
    assert_error_envelope(
        response.json(),
        code="analysis_failed",
        retryable=True,
        failed_agents=["flow", "risk"],
    )


async def test_post_evaluate_maps_timeout_to_upstream_timeout(
    monkeypatch,
) -> None:
    async def fake_evaluate(
        self: EvaluateSignalService,
        _candidate_event: object,
    ) -> object:
        raise TimeoutError("provider request timed out")

    monkeypatch.setattr(EvaluateSignalService, "evaluate", fake_evaluate)

    response = await post_evaluate_signal(build_candidate_event_payload())

    assert response.status_code == 503
    assert_error_envelope(
        response.json(),
        code="upstream_timeout",
        retryable=True,
        failed_agents=[],
    )


async def test_post_evaluate_maps_connection_error_to_upstream_unavailable(
    monkeypatch,
) -> None:
    async def fake_evaluate(
        self: EvaluateSignalService,
        _candidate_event: object,
    ) -> object:
        raise ConnectionError("provider unavailable")

    monkeypatch.setattr(EvaluateSignalService, "evaluate", fake_evaluate)

    response = await post_evaluate_signal(build_candidate_event_payload())

    assert response.status_code == 503
    assert_error_envelope(
        response.json(),
        code="upstream_unavailable",
        retryable=True,
        failed_agents=[],
    )


async def test_post_evaluate_maps_unexpected_failure_to_internal_error(
    monkeypatch,
) -> None:
    async def fake_evaluate(
        self: EvaluateSignalService,
        _candidate_event: object,
    ) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(EvaluateSignalService, "evaluate", fake_evaluate)

    response = await post_evaluate_signal(
        build_candidate_event_payload(),
        raise_app_exceptions=False,
    )
    body = response.json()

    assert response.status_code == 500
    assert_error_envelope(
        body,
        code="internal_error",
        retryable=True,
        failed_agents=[],
    )
    assert "boom" not in body["error"]["message"]
