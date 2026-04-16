from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.contracts.output import EvaluateSignalSuccessResponse


def build_approved_signal_card() -> dict[str, object]:
    return {
        "id": "sig_20260416_001",
        "title": "삼성전자에 강한 관심 신호가 포착됐어요",
        "asset": {
            "symbol": "005930",
            "name": "삼성전자",
            "market": "KR",
        },
        "signal_strength": "strong",
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
        ],
        "confidence": 0.76,
        "evidence_refs": [
            {"type": "market_event", "ref": "evt_123"},
            {"type": "news", "ref": "news_456"},
        ],
    }


def test_success_response_allows_reject_with_null_signal_card() -> None:
    payload = {
        "decision": "reject",
        "gate": {
            "score": 0.21,
            "reason": "event relevance is below briefing threshold",
        },
        "signal_card": None,
    }

    model = EvaluateSignalSuccessResponse.model_validate(payload)

    assert model.decision == "reject"
    assert model.signal_card is None


def test_success_response_requires_signal_card_for_approved_decision() -> None:
    payload = {
        "decision": "briefing",
        "gate": {
            "score": 0.65,
            "reason": "cleared briefing threshold",
        },
        "signal_card": None,
    }

    with pytest.raises(ValidationError):
        EvaluateSignalSuccessResponse.model_validate(payload)


def test_success_response_rejects_signal_card_on_reject_decision() -> None:
    payload = {
        "decision": "reject",
        "gate": {
            "score": 0.10,
            "reason": "event relevance is below briefing threshold",
        },
        "signal_card": build_approved_signal_card(),
    }

    with pytest.raises(ValidationError):
        EvaluateSignalSuccessResponse.model_validate(payload)


def test_success_response_accepts_approved_signal_card_shape() -> None:
    payload = {
        "decision": "instant_push",
        "gate": {
            "score": 0.82,
            "reason": "high multi-agent agreement with strong event relevance",
        },
        "signal_card": build_approved_signal_card(),
    }

    model = EvaluateSignalSuccessResponse.model_validate(payload)

    assert model.signal_card is not None
    assert len(model.signal_card.reasons) >= 2
    assert len(model.signal_card.risks) >= 1
    assert model.signal_card.agent_votes[0].agent == "chart"
    assert model.signal_card.confidence == 0.76
    assert model.signal_card.evidence_refs[0].type == "market_event"
    assert model.signal_card.broker_deeplink_hint.broker == "toss_securities"


def test_success_response_rejects_missing_required_approved_fields() -> None:
    signal_card = build_approved_signal_card()
    signal_card["reasons"] = ["거래량이 늘었습니다."]

    payload = {
        "decision": "briefing",
        "gate": {
            "score": 0.68,
            "reason": "cleared briefing threshold",
        },
        "signal_card": signal_card,
    }

    with pytest.raises(ValidationError):
        EvaluateSignalSuccessResponse.model_validate(payload)


def test_success_response_rejects_invalid_evidence_ref_and_broker_hint() -> None:
    signal_card = build_approved_signal_card()
    signal_card["evidence_refs"] = [{"type": "chart", "ref": "evt_123"}]
    signal_card["broker_deeplink_hint"] = {
        "broker": "other_broker",
        "symbol": "005930",
    }

    payload = {
        "decision": "briefing",
        "gate": {
            "score": 0.61,
            "reason": "cleared briefing threshold",
        },
        "signal_card": signal_card,
    }

    with pytest.raises(ValidationError):
        EvaluateSignalSuccessResponse.model_validate(payload)


def test_success_response_rejects_unsupported_agent_vote_stance() -> None:
    signal_card = build_approved_signal_card()
    signal_card["agent_votes"] = [
        {"agent": "chart", "stance": "bullish", "confidence": 0.78},
    ]

    payload = {
        "decision": "briefing",
        "gate": {
            "score": 0.61,
            "reason": "cleared briefing threshold",
        },
        "signal_card": signal_card,
    }

    with pytest.raises(ValidationError):
        EvaluateSignalSuccessResponse.model_validate(payload)


def test_success_response_rejects_blank_reason_or_risk_items() -> None:
    signal_card = build_approved_signal_card()
    signal_card["reasons"] = ["", "정상 이유"]

    payload = {
        "decision": "briefing",
        "gate": {
            "score": 0.61,
            "reason": "cleared briefing threshold",
        },
        "signal_card": signal_card,
    }

    with pytest.raises(ValidationError):
        EvaluateSignalSuccessResponse.model_validate(payload)

    signal_card = build_approved_signal_card()
    signal_card["risks"] = [""]

    payload = {
        "decision": "briefing",
        "gate": {
            "score": 0.61,
            "reason": "cleared briefing threshold",
        },
        "signal_card": signal_card,
    }

    with pytest.raises(ValidationError):
        EvaluateSignalSuccessResponse.model_validate(payload)
