from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.contracts.input import CandidateEventRequest


def build_valid_payload() -> dict[str, object]:
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
            "volume_ratio": 1.8,
        },
        "news_items": [
            {
                "id": "news_456",
                "headline": "반도체 업황 기대감 확대",
            },
        ],
        "flow_snapshot": {
            "foreign_net_buy": 1200000000,
        },
        "theme_context": ["반도체", {"theme": "AI"}],
        "metadata": {
            "gate_score": 0.72,
            "event_ref": "evt_123",
            "stub_agent_outputs": {
                "news": {
                    "summary": "업황 뉴스가 단기 모멘텀을 지지합니다.",
                    "stance": "positive",
                    "confidence": 0.81,
                },
            },
        },
    }


def test_candidate_event_request_accepts_spec_fields() -> None:
    payload = build_valid_payload()

    model = CandidateEventRequest.model_validate(payload)

    assert model.candidate_id == "cand_20260416_001"
    assert model.asset.symbol == "005930"
    assert model.event_ts == datetime.fromisoformat("2026-04-16T09:12:00+09:00")
    assert model.market_snapshot["price_change_pct"] == 3.2
    assert model.news_items[0]["id"] == "news_456"
    assert model.flow_snapshot["foreign_net_buy"] == 1200000000
    assert model.theme_context[0] == "반도체"
    assert model.metadata.gate_score == 0.72
    assert model.metadata.event_ref == "evt_123"
    assert model.metadata.stub_agent_outputs["news"]["stance"] == "positive"


def test_candidate_event_request_rejects_unknown_top_level_field() -> None:
    payload = build_valid_payload()
    payload["unexpected"] = True

    with pytest.raises(ValidationError):
        CandidateEventRequest.model_validate(payload)


def test_candidate_event_request_requires_all_spec_fields() -> None:
    payload = build_valid_payload()
    del payload["metadata"]

    with pytest.raises(ValidationError):
        CandidateEventRequest.model_validate(payload)


def test_candidate_event_request_rejects_empty_asset_symbol() -> None:
    payload = build_valid_payload()
    payload["asset"] = {
        "symbol": "",
        "name": "삼성전자",
        "market": "KR",
    }

    with pytest.raises(ValidationError):
        CandidateEventRequest.model_validate(payload)
