from __future__ import annotations

import time

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def build_candidate_event_payload(
    *,
    gate_score: float,
    stub_agent_outputs: dict[str, object],
) -> dict[str, object]:
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
            "gate_score": gate_score,
            "event_ref": "evt_123",
            "stub_agent_outputs": stub_agent_outputs,
        },
    }


def build_briefing_stub_outputs() -> dict[str, object]:
    return {
        "news": {
            "summary": "업황 뉴스가 단기 모멘텀을 지지합니다.",
            "stance": "positive",
            "confidence": 0.81,
        },
        "chart": {
            "summary": "가격과 거래량이 함께 살아났습니다.",
            "stance": "positive",
            "confidence": 0.78,
        },
        "flow": {
            "summary": "수급 유입은 있지만 아직 강한 확신 단계는 아닙니다.",
            "stance": "neutral",
            "confidence": 0.55,
        },
        "risk": {
            "summary": "단기 과열 이후 변동성이 커질 수 있습니다.",
            "stance": "cautious",
            "confidence": 0.64,
        },
        "editor": {
            "title": "삼성전자에 관심 신호가 포착됐어요",
            "summary": "가격 반등과 거래량 증가, 관련 뉴스가 함께 나타났습니다.",
            "reasons": [
                "거래량이 평소 대비 크게 증가했습니다.",
                "관련 업황 뉴스가 동시에 유입됐습니다.",
            ],
            "risks": [
                "단기 과열 후 되돌림 가능성이 있습니다.",
            ],
            "watch_action": "오늘 장 마감 전 수급 흐름이 유지되는지 확인해보세요.",
        },
    }


@pytest.mark.skip(reason="measurement-only baseline; not a regression gate")
async def test_measure_evaluate_signal_baseline() -> None:
    transport = ASGITransport(app=app)
    reject_payload = build_candidate_event_payload(
        gate_score=0.20,
        stub_agent_outputs={},
    )
    briefing_payload = build_candidate_event_payload(
        gate_score=0.70,
        stub_agent_outputs=build_briefing_stub_outputs(),
    )

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for _ in range(3):
            warmup_response = await client.post(
                "/v1/signals/evaluate",
                json=briefing_payload,
            )
            assert warmup_response.status_code == 200

        reject_durations: list[float] = []
        briefing_durations: list[float] = []

        for _ in range(20):
            reject_started = time.perf_counter()
            reject_response = await client.post(
                "/v1/signals/evaluate",
                json=reject_payload,
            )
            reject_durations.append((time.perf_counter() - reject_started) * 1000)
            assert reject_response.status_code == 200

            briefing_started = time.perf_counter()
            briefing_response = await client.post(
                "/v1/signals/evaluate",
                json=briefing_payload,
            )
            briefing_durations.append((time.perf_counter() - briefing_started) * 1000)
            assert briefing_response.status_code == 200

    reject_avg_ms = sum(reject_durations) / len(reject_durations)
    briefing_avg_ms = sum(briefing_durations) / len(briefing_durations)

    print(f"reject_avg_ms={reject_avg_ms:.3f}")
    print(f"briefing_avg_ms={briefing_avg_ms:.3f}")

    assert reject_avg_ms > 0
    assert briefing_avg_ms > 0
