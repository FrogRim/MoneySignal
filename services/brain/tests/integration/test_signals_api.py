from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient, Response

from app import main as main_module
from app.contracts.output import EvaluateSignalSuccessResponse
from app.main import app
from app.orchestrators.evaluate_signal import EvaluateSignalService


@pytest.fixture(autouse=True)
def clear_rate_limit_buckets() -> None:
    main_module._RATE_LIMIT_BUCKETS.clear()
    yield
    main_module._RATE_LIMIT_BUCKETS.clear()


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


def build_signal_card_payload() -> dict[str, object]:
    return {
        "id": "sig_20260416_001",
        "title": "삼성전자에 관심 신호가 포착됐어요",
        "asset": {
            "symbol": "005930",
            "name": "삼성전자",
            "market": "KR",
        },
        "signal_strength": "watch",
        "summary": "가격 반등과 거래량 증가, 관련 업황 뉴스가 함께 나타났습니다.",
        "reasons": [
            "거래량이 평소 대비 크게 증가했습니다.",
            "관련 업황 뉴스가 동시에 유입됐습니다.",
        ],
        "risks": [
            "단기 과열 후 되돌림 가능성이 있습니다.",
        ],
        "watch_action": "오늘 장 마감 전 수급 흐름이 유지되는지 확인해보세요.",
        "broker_deeplink_hint": {
            "broker": "toss_securities",
            "symbol": "005930",
        },
        "agent_votes": [
            {"agent": "chart", "stance": "positive", "confidence": 0.78},
            {"agent": "news", "stance": "positive", "confidence": 0.81},
            {"agent": "flow", "stance": "neutral", "confidence": 0.55},
            {"agent": "risk", "stance": "cautious", "confidence": 0.64},
        ],
        "confidence": 0.76,
        "evidence_refs": [
            {"type": "market_event", "ref": "evt_123"},
            {"type": "news", "ref": "news_1"},
        ],
    }


def build_instant_push_signal_card_payload() -> dict[str, object]:
    signal_card = build_signal_card_payload()
    signal_card["signal_strength"] = "strong"
    return signal_card


def build_success_payload(
    *,
    decision: str,
    score: float,
    reason: str,
    signal_card: dict[str, object] | None,
) -> dict[str, object]:
    return {
        "decision": decision,
        "gate": {
            "score": score,
            "reason": reason,
        },
        "signal_card": signal_card,
    }


async def post_evaluate_signal(
    payload: dict[str, object],
    *,
    headers: dict[str, str] | None = None,
    client_host: tuple[str, int] = ("127.0.0.1", 123),
) -> Response:
    transport = ASGITransport(app=app, client=client_host)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.post(
            "/v1/signals/evaluate",
            json=payload,
            headers=headers,
        )


async def test_post_evaluate_returns_briefing_success_envelope(
    monkeypatch,
) -> None:
    expected_payload = build_success_payload(
        decision="briefing",
        score=0.70,
        reason="event relevance passed the briefing threshold",
        signal_card=build_signal_card_payload(),
    )

    async def fake_evaluate(
        self: EvaluateSignalService,
        _candidate_event: object,
    ) -> EvaluateSignalSuccessResponse:
        return EvaluateSignalSuccessResponse.model_validate(expected_payload)

    monkeypatch.setattr(EvaluateSignalService, "evaluate", fake_evaluate)

    response = await post_evaluate_signal(build_candidate_event_payload())

    assert response.status_code == 200
    assert response.json() == expected_payload


async def test_post_evaluate_returns_reject_with_null_signal_card(
    monkeypatch,
) -> None:
    expected_payload = build_success_payload(
        decision="reject",
        score=0.20,
        reason="event relevance is below briefing threshold",
        signal_card=None,
    )

    async def fake_evaluate(
        self: EvaluateSignalService,
        _candidate_event: object,
    ) -> EvaluateSignalSuccessResponse:
        return EvaluateSignalSuccessResponse.model_validate(expected_payload)

    monkeypatch.setattr(EvaluateSignalService, "evaluate", fake_evaluate)

    response = await post_evaluate_signal(build_candidate_event_payload())

    assert response.status_code == 200
    assert response.json() == expected_payload


async def test_post_evaluate_returns_instant_push_success_envelope(
    monkeypatch,
) -> None:
    expected_payload = build_success_payload(
        decision="instant_push",
        score=0.91,
        reason="high multi-agent agreement with strong event relevance",
        signal_card=build_instant_push_signal_card_payload(),
    )

    async def fake_evaluate(
        self: EvaluateSignalService,
        _candidate_event: object,
    ) -> EvaluateSignalSuccessResponse:
        return EvaluateSignalSuccessResponse.model_validate(expected_payload)

    monkeypatch.setattr(EvaluateSignalService, "evaluate", fake_evaluate)

    response = await post_evaluate_signal(build_candidate_event_payload())

    assert response.status_code == 200
    assert response.json() == expected_payload


async def test_openapi_declares_structured_error_responses(
) -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200

    post_operation = response.json()["paths"]["/v1/signals/evaluate"]["post"]
    responses = post_operation["responses"]

    assert responses["200"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/EvaluateSignalSuccessResponse"
    )
    assert responses["422"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ErrorEnvelope"
    )
    assert responses["429"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ErrorEnvelope"
    )
    assert responses["503"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ErrorEnvelope"
    )
    assert responses["500"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ErrorEnvelope"
    )


async def test_post_evaluate_returns_request_id_header_on_success(
    monkeypatch,
) -> None:
    expected_payload = build_success_payload(
        decision="briefing",
        score=0.70,
        reason="event relevance passed the briefing threshold",
        signal_card=build_signal_card_payload(),
    )

    async def fake_evaluate(
        self: EvaluateSignalService,
        _candidate_event: object,
    ) -> EvaluateSignalSuccessResponse:
        return EvaluateSignalSuccessResponse.model_validate(expected_payload)

    monkeypatch.setattr(EvaluateSignalService, "evaluate", fake_evaluate)

    response = await post_evaluate_signal(build_candidate_event_payload())

    assert response.status_code == 200
    assert response.headers["x-request-id"]


async def test_post_evaluate_applies_cors_headers_for_allowed_origin(
    monkeypatch,
) -> None:
    expected_payload = build_success_payload(
        decision="briefing",
        score=0.70,
        reason="event relevance passed the briefing threshold",
        signal_card=build_signal_card_payload(),
    )

    async def fake_evaluate(
        self: EvaluateSignalService,
        _candidate_event: object,
    ) -> EvaluateSignalSuccessResponse:
        return EvaluateSignalSuccessResponse.model_validate(expected_payload)

    monkeypatch.setattr(EvaluateSignalService, "evaluate", fake_evaluate)
    os.environ["BRAIN_CORS_ALLOW_ORIGINS"] = "https://app.example.com"

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/v1/signals/evaluate",
                json=build_candidate_event_payload(),
                headers={"Origin": "https://app.example.com"},
            )
    finally:
        os.environ.pop("BRAIN_CORS_ALLOW_ORIGINS", None)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.example.com"
    assert response.headers["vary"] == "Origin"


async def test_post_evaluate_rejects_requests_after_rate_limit_is_exceeded(
    monkeypatch,
) -> None:
    expected_payload = build_success_payload(
        decision="briefing",
        score=0.70,
        reason="event relevance passed the briefing threshold",
        signal_card=build_signal_card_payload(),
    )

    async def fake_evaluate(
        self: EvaluateSignalService,
        _candidate_event: object,
    ) -> EvaluateSignalSuccessResponse:
        return EvaluateSignalSuccessResponse.model_validate(expected_payload)

    monkeypatch.setattr(EvaluateSignalService, "evaluate", fake_evaluate)
    os.environ["BRAIN_RATE_LIMIT_ENABLED"] = "true"
    os.environ["BRAIN_RATE_LIMIT_MAX_REQUESTS"] = "2"
    os.environ["BRAIN_RATE_LIMIT_WINDOW_SECONDS"] = "60"

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            first_response = await client.post(
                "/v1/signals/evaluate",
                json=build_candidate_event_payload(),
            )
            second_response = await client.post(
                "/v1/signals/evaluate",
                json=build_candidate_event_payload(),
            )
            limited_response = await client.post(
                "/v1/signals/evaluate",
                json=build_candidate_event_payload(),
            )
    finally:
        os.environ.pop("BRAIN_RATE_LIMIT_ENABLED", None)
        os.environ.pop("BRAIN_RATE_LIMIT_MAX_REQUESTS", None)
        os.environ.pop("BRAIN_RATE_LIMIT_WINDOW_SECONDS", None)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert limited_response.status_code == 429
    body = limited_response.json()
    assert body["error"]["code"] == "rate_limited"
    assert body["error"]["retryable"] is True
    assert body["error"]["failed_agents"] == []
    assert body["error"]["trace_id"] == limited_response.headers["x-request-id"]


async def test_post_evaluate_ignores_forwarded_header_from_untrusted_client(
    monkeypatch,
) -> None:
    expected_payload = build_success_payload(
        decision="briefing",
        score=0.70,
        reason="event relevance passed the briefing threshold",
        signal_card=build_signal_card_payload(),
    )

    async def fake_evaluate(
        self: EvaluateSignalService,
        _candidate_event: object,
    ) -> EvaluateSignalSuccessResponse:
        return EvaluateSignalSuccessResponse.model_validate(expected_payload)

    monkeypatch.setattr(EvaluateSignalService, "evaluate", fake_evaluate)
    os.environ["BRAIN_RATE_LIMIT_ENABLED"] = "true"
    os.environ["BRAIN_RATE_LIMIT_MAX_REQUESTS"] = "1"
    os.environ["BRAIN_RATE_LIMIT_WINDOW_SECONDS"] = "60"
    os.environ["BRAIN_RATE_LIMIT_TRUST_X_FORWARDED_FOR"] = "true"

    try:
        first_response = await post_evaluate_signal(
            build_candidate_event_payload(),
            headers={"X-Forwarded-For": "198.51.100.1"},
            client_host=("10.0.0.8", 123),
        )
        limited_response = await post_evaluate_signal(
            build_candidate_event_payload(),
            headers={"X-Forwarded-For": "198.51.100.2"},
            client_host=("10.0.0.8", 123),
        )
    finally:
        os.environ.pop("BRAIN_RATE_LIMIT_ENABLED", None)
        os.environ.pop("BRAIN_RATE_LIMIT_MAX_REQUESTS", None)
        os.environ.pop("BRAIN_RATE_LIMIT_WINDOW_SECONDS", None)
        os.environ.pop("BRAIN_RATE_LIMIT_TRUST_X_FORWARDED_FOR", None)

    assert first_response.status_code == 200
    assert limited_response.status_code == 429
    assert limited_response.json()["error"]["code"] == "rate_limited"


async def test_post_evaluate_can_trust_forwarded_header_from_trusted_proxy(
    monkeypatch,
) -> None:
    expected_payload = build_success_payload(
        decision="briefing",
        score=0.70,
        reason="event relevance passed the briefing threshold",
        signal_card=build_signal_card_payload(),
    )

    async def fake_evaluate(
        self: EvaluateSignalService,
        _candidate_event: object,
    ) -> EvaluateSignalSuccessResponse:
        return EvaluateSignalSuccessResponse.model_validate(expected_payload)

    monkeypatch.setattr(EvaluateSignalService, "evaluate", fake_evaluate)
    os.environ["BRAIN_RATE_LIMIT_ENABLED"] = "true"
    os.environ["BRAIN_RATE_LIMIT_MAX_REQUESTS"] = "1"
    os.environ["BRAIN_RATE_LIMIT_WINDOW_SECONDS"] = "60"
    os.environ["BRAIN_RATE_LIMIT_TRUST_X_FORWARDED_FOR"] = "true"
    os.environ["BRAIN_RATE_LIMIT_TRUSTED_PROXY_CLIENTS"] = "10.0.0.8"

    try:
        first_response = await post_evaluate_signal(
            build_candidate_event_payload(),
            headers={"X-Forwarded-For": "198.51.100.1"},
            client_host=("10.0.0.8", 123),
        )
        second_response = await post_evaluate_signal(
            build_candidate_event_payload(),
            headers={"X-Forwarded-For": "198.51.100.2"},
            client_host=("10.0.0.8", 123),
        )
    finally:
        os.environ.pop("BRAIN_RATE_LIMIT_ENABLED", None)
        os.environ.pop("BRAIN_RATE_LIMIT_MAX_REQUESTS", None)
        os.environ.pop("BRAIN_RATE_LIMIT_WINDOW_SECONDS", None)
        os.environ.pop("BRAIN_RATE_LIMIT_TRUST_X_FORWARDED_FOR", None)
        os.environ.pop("BRAIN_RATE_LIMIT_TRUSTED_PROXY_CLIENTS", None)

    assert first_response.status_code == 200
    assert second_response.status_code == 200


async def test_health_accepts_ipv6_host_when_trusted_hosts_configured() -> None:
    os.environ["BRAIN_TRUSTED_HOSTS"] = "2001:db8::1"

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.get(
                "/health",
                headers={"Host": "[2001:db8::1]:8000"},
            )
    finally:
        os.environ.pop("BRAIN_TRUSTED_HOSTS", None)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
