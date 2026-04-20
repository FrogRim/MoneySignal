from __future__ import annotations

import importlib
import json

import pytest
from httpx import (
    ASGITransport,
    AsyncClient,
    ConnectError,
    MockTransport,
    ReadTimeout,
    Request,
    Response,
)
from pydantic import ValidationError

from app import main as main_module
from app.contracts import BrainEvaluationResult
from app.main import app
from app.services.feed_store import InMemoryFeedStore


@pytest.fixture(autouse=True)
def reset_store(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "_store", InMemoryFeedStore())


def build_candidate(candidate_id: str, score: float) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "asset": {
            "symbol": "005930",
            "name": "삼성전자",
            "market": "KR",
        },
        "trigger_type": "price_volume_breakout",
        "event_ts": "2026-04-19T09:00:00+00:00",
        "market_snapshot": {"price_change_pct": 3.2},
        "news_items": [{"id": "news_1", "headline": "headline_1"}],
        "flow_snapshot": {"foreign_net_buy": 1200000000},
        "theme_context": [{"theme": "ai"}],
        "metadata": {
            "gate_score": score,
            "event_ref": f"evt_{candidate_id}",
            "stub_agent_outputs": {},
        },
    }


def build_brain_success(
    *,
    candidate_id: str,
    decision: str,
    signal_id: str,
) -> dict[str, object]:
    return {
        "decision": decision,
        "gate": {
            "score": 0.72,
            "reason": "event relevance passed the briefing threshold",
        },
        "signal_card": {
            "id": signal_id,
            "title": f"{candidate_id} title",
            "asset": {
                "symbol": "005930",
                "name": "삼성전자",
                "market": "KR",
            },
            "signal_strength": "watch",
            "summary": f"{candidate_id} summary",
            "reasons": ["reason 1", "reason 2"],
            "risks": ["risk 1"],
            "watch_action": "watch this",
            "broker_deeplink_hint": {
                "broker": "toss_securities",
                "symbol": "005930",
            },
            "agent_votes": [
                {"agent": "chart", "stance": "positive", "confidence": 0.78}
            ],
            "confidence": 0.76,
            "evidence_refs": [{"type": "market_event", "ref": "evt_1"}],
        },
    }


def build_brain_http_success(
    *,
    candidate_id: str,
    decision: str,
    signal_id: str,
) -> dict[str, object]:
    return build_brain_success(
        candidate_id=candidate_id,
        decision=decision,
        signal_id=signal_id,
    )


async def test_evaluate_candidate_event_rejects_malformed_brain_output() -> None:
    candidate_event = build_candidate("cand_invalid", 0.7)
    metadata = candidate_event["metadata"]
    assert isinstance(metadata, dict)
    stub_agent_outputs = metadata["stub_agent_outputs"]
    assert isinstance(stub_agent_outputs, dict)
    stub_agent_outputs["brain"] = {
        "decision": "briefing",
        "gate": {
            "score": 0.72,
            "reason": "event relevance passed the briefing threshold",
        },
        "signal_card": {
            "id": "sig_invalid",
            "title": "invalid title",
            "asset": {
                "symbol": "005930",
                "name": "삼성전자",
                "market": "KR",
            },
            "signal_strength": "watch",
            "summary": "invalid summary",
            "reasons": ["reason 1"],
            "risks": ["risk 1"],
            "watch_action": "watch this",
            "broker_deeplink_hint": {
                "broker": "toss_securities",
                "symbol": "005930",
            },
            "agent_votes": [],
            "confidence": 0.76,
            "evidence_refs": [{"type": "market_event", "ref": "evt_invalid"}],
        },
    }

    with pytest.raises(ValidationError):
        await main_module.evaluate_candidate_event(candidate_event)


async def test_evaluate_candidate_event_calls_brain_http_endpoint(monkeypatch) -> None:
    candidate_event = build_candidate("cand_http", 0.7)
    monkeypatch.setenv("PIPELINE_BRAIN_BASE_URL", "http://brain.test")

    def handler(request: Request) -> Response:
        assert request.method == "POST"
        assert str(request.url) == "http://brain.test/v1/signals/evaluate"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["candidate_id"] == "cand_http"
        assert payload["asset"]["symbol"] == "005930"
        return Response(
            status_code=200,
            json=build_brain_http_success(
                candidate_id="cand_http",
                decision="briefing",
                signal_id="sig_http",
            ),
        )

    monkeypatch.setattr(
        main_module,
        "build_brain_transport",
        lambda: MockTransport(handler),
    )

    brain_result = await main_module.evaluate_candidate_event(candidate_event)

    assert brain_result.decision.value == "briefing"
    assert brain_result.signal_card is not None
    assert brain_result.signal_card.id == "sig_http"


async def test_evaluate_candidate_event_raises_runtime_error_for_brain_timeout(
    monkeypatch,
) -> None:
    candidate_event = build_candidate("cand_timeout", 0.7)
    monkeypatch.setenv("PIPELINE_BRAIN_BASE_URL", "http://brain.test")

    def handler(request: Request) -> Response:
        raise ReadTimeout("timed out", request=request)

    monkeypatch.setattr(
        main_module,
        "build_brain_transport",
        lambda: MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="brain evaluation timed out"):
        await main_module.evaluate_candidate_event(candidate_event)


async def test_evaluate_candidate_event_raises_runtime_error_for_brain_unavailable(
    monkeypatch,
) -> None:
    candidate_event = build_candidate("cand_unavailable", 0.7)
    monkeypatch.setenv("PIPELINE_BRAIN_BASE_URL", "http://brain.test")

    def handler(request: Request) -> Response:
        raise ConnectError("connect failed", request=request)

    monkeypatch.setattr(
        main_module,
        "build_brain_transport",
        lambda: MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="brain evaluation unavailable"):
        await main_module.evaluate_candidate_event(candidate_event)


async def test_evaluate_candidate_event_raises_runtime_error_for_brain_error_envelope(
    monkeypatch,
) -> None:
    candidate_event = build_candidate("cand_error", 0.7)
    monkeypatch.setenv("PIPELINE_BRAIN_BASE_URL", "http://brain.test")

    def handler(request: Request) -> Response:
        return Response(
            status_code=503,
            json={
                "error": {
                    "code": "upstream_timeout",
                    "message": "upstream evaluation timed out",
                    "retryable": True,
                    "failed_agents": [],
                    "trace_id": "req_test123",
                }
            },
        )

    monkeypatch.setattr(
        main_module,
        "build_brain_transport",
        lambda: MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="brain evaluation failed: upstream_timeout"):
        await main_module.evaluate_candidate_event(candidate_event)


async def test_evaluate_candidate_event_handles_non_json_brain_response(
    monkeypatch,
) -> None:
    candidate_event = build_candidate("cand_non_json", 0.7)
    monkeypatch.setenv("PIPELINE_BRAIN_BASE_URL", "http://brain.test")

    def handler(request: Request) -> Response:
        return Response(
            status_code=503,
            content="bad gateway",
            headers={"content-type": "text/plain"},
        )

    monkeypatch.setattr(
        main_module,
        "build_brain_transport",
        lambda: MockTransport(handler),
    )

    with pytest.raises(RuntimeError, match="brain returned invalid JSON"):
        await main_module.evaluate_candidate_event(candidate_event)


async def test_rebuild_feed_skips_brain_operational_failures(monkeypatch) -> None:
    monkeypatch.setenv("PIPELINE_ENV", "test")
    fixtures = [
        build_candidate("cand_timeout", 0.7),
        build_candidate("cand_valid", 0.8),
    ]

    async def fake_evaluate(
        candidate_event: dict[str, object],
    ) -> BrainEvaluationResult:
        candidate_id = candidate_event["candidate_id"]
        assert isinstance(candidate_id, str)
        if candidate_id == "cand_timeout":
            raise main_module.BrainOperationalError("brain evaluation timed out")
        return BrainEvaluationResult.model_validate(
            build_brain_success(
                candidate_id="cand_valid",
                decision="briefing",
                signal_id="sig_valid",
            )
        )

    monkeypatch.setattr(main_module, "load_candidate_fixtures", lambda: fixtures)
    monkeypatch.setattr(main_module, "evaluate_candidate_event", fake_evaluate)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        rebuild_response = await client.post("/internal/rebuild-feed")
        feed_response = await client.get("/feed")

    assert rebuild_response.status_code == 200
    assert rebuild_response.json() == {
        "processedCandidates": 2,
        "publishedSignals": 1,
        "rejectedCandidates": 1,
    }
    assert feed_response.status_code == 200
    assert [item["id"] for item in feed_response.json()["items"]] == ["sig_valid"]


async def test_rebuild_feed_publishes_only_non_reject_signals(monkeypatch) -> None:
    monkeypatch.setenv("PIPELINE_ENV", "test")
    fixtures = [
        build_candidate("cand_001", 0.7),
        build_candidate("cand_002", 0.2),
        build_candidate("cand_003", 0.9),
    ]
    brain_results = {
        "cand_001": build_brain_success(
            candidate_id="cand_001",
            decision="briefing",
            signal_id="sig_001",
        ),
        "cand_002": {
            "decision": "reject",
            "gate": {
                "score": 0.2,
                "reason": "event relevance is below briefing threshold",
            },
            "signal_card": None,
        },
        "cand_003": build_brain_success(
            candidate_id="cand_003",
            decision="instant_push",
            signal_id="sig_003",
        ),
    }

    async def fake_evaluate(
        candidate_event: dict[str, object],
    ) -> BrainEvaluationResult:
        candidate_id = candidate_event["candidate_id"]
        assert isinstance(candidate_id, str)
        return BrainEvaluationResult.model_validate(brain_results[candidate_id])

    monkeypatch.setattr(main_module, "load_candidate_fixtures", lambda: fixtures)
    monkeypatch.setattr(main_module, "evaluate_candidate_event", fake_evaluate)

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        rebuild_response = await client.post("/internal/rebuild-feed")
        feed_response = await client.get("/feed")
        detail_response = await client.get("/signals/sig_003")

    assert rebuild_response.status_code == 200
    assert rebuild_response.json() == {
        "processedCandidates": 3,
        "publishedSignals": 2,
        "rejectedCandidates": 1,
    }

    assert feed_response.status_code == 200
    assert [item["id"] for item in feed_response.json()["items"]] == [
        "sig_003",
        "sig_001",
    ]

    assert detail_response.status_code == 200
    assert detail_response.json()["signal"]["id"] == "sig_003"
    assert detail_response.json()["signal"]["decision"] == "instant_push"


async def test_rebuild_feed_rejects_request_without_internal_token_outside_local(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PIPELINE_ENV", "production")
    monkeypatch.setenv("PIPELINE_INTERNAL_REBUILD_TOKEN", "secret-token")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/internal/rebuild-feed")

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "forbidden",
            "message": "internal rebuild is not allowed",
        }
    }


async def test_rebuild_feed_rejects_request_when_env_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("PIPELINE_ENV", raising=False)
    monkeypatch.setenv("PIPELINE_INTERNAL_REBUILD_TOKEN", "secret-token")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/internal/rebuild-feed")

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "forbidden",
            "message": "internal rebuild is not allowed",
        }
    }


async def test_rebuild_feed_rejects_request_with_wrong_internal_token(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PIPELINE_ENV", "production")
    monkeypatch.setenv("PIPELINE_INTERNAL_REBUILD_TOKEN", "secret-token")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/internal/rebuild-feed",
            headers={"x-pipeline-internal-token": "wrong-token"},
        )

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "forbidden",
            "message": "internal rebuild is not allowed",
        }
    }


async def test_rebuild_feed_accepts_matching_internal_token_outside_local(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PIPELINE_ENV", "production")
    monkeypatch.setenv("PIPELINE_INTERNAL_REBUILD_TOKEN", "secret-token")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        rebuild_response = await client.post(
            "/internal/rebuild-feed",
            headers={"x-pipeline-internal-token": "secret-token"},
        )

    assert rebuild_response.status_code == 200
    assert rebuild_response.json() == {
        "processedCandidates": 1,
        "publishedSignals": 1,
        "rejectedCandidates": 0,
    }


async def test_rebuild_feed_uses_default_stubbed_fixture_data(monkeypatch) -> None:
    monkeypatch.setenv("PIPELINE_ENV", "test")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        rebuild_response = await client.post("/internal/rebuild-feed")
        feed_response = await client.get("/feed")
        detail_response = await client.get("/signals/sig_fixture_001")

    assert rebuild_response.status_code == 200
    assert rebuild_response.json() == {
        "processedCandidates": 1,
        "publishedSignals": 1,
        "rejectedCandidates": 0,
    }
    assert feed_response.status_code == 200
    assert [item["id"] for item in feed_response.json()["items"]] == ["sig_fixture_001"]
    assert detail_response.status_code == 200
    assert detail_response.json()["signal"]["id"] == "sig_fixture_001"
    assert detail_response.json()["signal"]["decision"] == "briefing"


async def test_rebuild_feed_skips_invalid_brain_candidate_and_keeps_valid_ones(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PIPELINE_ENV", "test")
    fixtures = [
        build_candidate("cand_invalid", 0.7),
        build_candidate("cand_valid", 0.8),
    ]
    brain_results = {
        "cand_invalid": {
            "decision": "briefing",
            "gate": {
                "score": 0.72,
                "reason": "event relevance passed the briefing threshold",
            },
            "signal_card": {
                "id": "sig_invalid",
                "title": "invalid title",
                "asset": {
                    "symbol": "005930",
                    "name": "삼성전자",
                    "market": "KR",
                },
                "signal_strength": "watch",
                "summary": "invalid summary",
                "reasons": ["reason 1"],
                "risks": ["risk 1"],
                "watch_action": "watch this",
                "broker_deeplink_hint": {
                    "broker": "toss_securities",
                    "symbol": "005930",
                },
                "agent_votes": [],
                "confidence": 0.76,
                "evidence_refs": [{"type": "market_event", "ref": "evt_invalid"}],
            },
        },
        "cand_valid": build_brain_success(
            candidate_id="cand_valid",
            decision="briefing",
            signal_id="sig_valid",
        ),
    }

    async def fake_evaluate(
        candidate_event: dict[str, object],
    ) -> BrainEvaluationResult:
        candidate_id = candidate_event["candidate_id"]
        assert isinstance(candidate_id, str)
        return BrainEvaluationResult.model_validate(brain_results[candidate_id])

    monkeypatch.setattr(main_module, "load_candidate_fixtures", lambda: fixtures)
    monkeypatch.setattr(main_module, "evaluate_candidate_event", fake_evaluate)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        rebuild_response = await client.post("/internal/rebuild-feed")
        feed_response = await client.get("/feed")

    assert rebuild_response.status_code == 200
    assert rebuild_response.json() == {
        "processedCandidates": 2,
        "publishedSignals": 1,
        "rejectedCandidates": 1,
    }
    assert feed_response.status_code == 200
    assert [item["id"] for item in feed_response.json()["items"]] == ["sig_valid"]


async def test_get_session_returns_active_by_default(monkeypatch) -> None:
    monkeypatch.delenv("PIPELINE_SESSION_STATUS", raising=False)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/session")

    assert response.status_code == 200
    assert response.json() == {"status": "active"}


@pytest.mark.parametrize(
    ("session_status", "expected_status"),
    [
        ("expired", "expired"),
        ("unauthenticated", "unauthenticated"),
    ],
)
async def test_get_session_returns_configured_status(
    monkeypatch,
    session_status: str,
    expected_status: str,
) -> None:
    monkeypatch.setenv("PIPELINE_SESSION_STATUS", session_status)
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/session")

    assert response.status_code == 200
    assert response.json() == {"status": expected_status}


async def test_get_session_defaults_to_active_for_unknown_status(monkeypatch) -> None:
    monkeypatch.setenv("PIPELINE_SESSION_STATUS", "surprising")
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/session")

    assert response.status_code == 200
    assert response.json() == {"status": "active"}


async def test_get_session_returns_cors_headers_for_allowed_origin(monkeypatch) -> None:
    monkeypatch.setenv("PIPELINE_CORS_ALLOW_ORIGINS", "https://app.moneysignal.lol")
    reloaded_module = importlib.reload(main_module)
    transport = ASGITransport(app=reloaded_module.app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/session",
            headers={"Origin": "https://app.moneysignal.lol"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.moneysignal.lol"


async def test_get_signal_returns_not_found_error_for_unknown_id() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/signals/sig_missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "signal not found",
        }
    }
