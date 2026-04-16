from __future__ import annotations

import pytest

from app.config import BrainSettings
from app.contracts.input import CandidateEventRequest
from app.contracts.output import SignalDecision
from app.orchestrators.evaluate_signal import AnalysisFailedError, EvaluateSignalService


def build_candidate_event_request(
    *,
    gate_score: float,
    stub_agent_outputs: dict[str, object],
) -> CandidateEventRequest:
    payload = {
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
    return CandidateEventRequest.model_validate(payload)


def build_service() -> EvaluateSignalService:
    return EvaluateSignalService(settings=BrainSettings())


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
                "단기 과열 뒤 변동성이 커질 수 있습니다.",
            ],
            "watch_action": "오늘 장 마감 전 수급 흐름이 유지되는지 확인해보세요.",
        },
    }


def build_instant_push_stub_outputs() -> dict[str, object]:
    return {
        "news": {
            "summary": "호재성 뉴스가 강하게 유입됐습니다.",
            "stance": "positive",
            "confidence": 0.91,
        },
        "chart": {
            "summary": "가격 돌파 흐름이 분명합니다.",
            "stance": "positive",
            "confidence": 0.88,
        },
        "flow": {
            "summary": "수급 유입이 강하게 유지되고 있습니다.",
            "stance": "positive",
            "confidence": 0.86,
        },
        "risk": {
            "summary": "추격 매수 심리는 경계할 필요가 있습니다.",
            "stance": "positive",
            "confidence": 0.84,
        },
        "editor": {
            "title": "삼성전자에 강한 관심 신호가 포착됐어요",
            "summary": "가격과 수급, 뉴스 흐름이 동시에 강해졌습니다.",
            "reasons": [
                "가격 돌파와 거래량 증가가 함께 나타났습니다.",
                "관련 뉴스와 수급 흐름이 같은 방향을 가리킵니다.",
            ],
            "risks": [
                "급등 직후 변동성이 커질 수 있습니다.",
            ],
            "watch_action": "지속적인 거래대금 유입이 이어지는지 확인해보세요.",
        },
    }


async def test_evaluate_returns_briefing_signal_card_with_disagreement_visible(
) -> None:
    service = build_service()
    request = build_candidate_event_request(
        gate_score=0.70,
        stub_agent_outputs=build_briefing_stub_outputs(),
    )

    result = await service.evaluate(request)

    assert result.decision == SignalDecision.BRIEFING
    assert result.gate.score == 0.70
    assert result.signal_card is not None
    assert result.signal_card.signal_strength == "watch"
    assert result.signal_card.title == "삼성전자에 관심 신호가 포착됐어요"
    assert result.signal_card.confidence == 0.76
    assert [
        (vote.agent, vote.stance.value)
        for vote in result.signal_card.agent_votes
    ] == [
        ("news", "positive"),
        ("chart", "positive"),
        ("flow", "neutral"),
        ("risk", "cautious"),
    ]
    assert [ref.model_dump() for ref in result.signal_card.evidence_refs] == [
        {"type": "market_event", "ref": "evt_123"},
        {"type": "news", "ref": "news_1"},
        {"type": "news", "ref": "news_2"},
    ]


async def test_evaluate_returns_instant_push_signal_card() -> None:
    service = build_service()
    request = build_candidate_event_request(
        gate_score=0.91,
        stub_agent_outputs=build_instant_push_stub_outputs(),
    )

    result = await service.evaluate(request)

    assert result.decision == SignalDecision.INSTANT_PUSH
    assert result.gate.score == 0.91
    assert result.signal_card is not None
    assert result.signal_card.signal_strength == "strong"
    assert result.signal_card.broker_deeplink_hint.model_dump() == {
        "broker": "toss_securities",
        "symbol": "005930",
    }


async def test_evaluate_returns_reject_without_running_agents() -> None:
    service = build_service()
    request = build_candidate_event_request(
        gate_score=0.20,
        stub_agent_outputs={},
    )

    result = await service.evaluate(request)

    assert result.decision == SignalDecision.REJECT
    assert result.signal_card is None


async def test_evaluate_raises_analysis_failed_when_minimum_coverage_is_not_met(
) -> None:
    service = build_service()
    request = build_candidate_event_request(
        gate_score=0.72,
        stub_agent_outputs={
            "news": {
                "summary": "뉴스 모멘텀은 긍정적입니다.",
                "stance": "positive",
                "confidence": 0.81,
            },
            "chart": {
                "summary": "차트 흐름은 개선되고 있습니다.",
                "stance": "positive",
                "confidence": 0.78,
            },
        },
    )

    with pytest.raises(AnalysisFailedError) as exc_info:
        await service.evaluate(request)

    assert exc_info.value.failed_agents == ["flow", "risk"]
    assert "minimum specialist coverage" in str(exc_info.value)
