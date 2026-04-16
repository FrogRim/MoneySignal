from __future__ import annotations

from app.contracts.input import CandidateEventRequest
from app.prompts.builders import build_prompt


def build_candidate_event_request() -> CandidateEventRequest:
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
            {"id": f"news_{index}", "headline": f"headline_{index}"}
            for index in range(1, 8)
        ],
        "flow_snapshot": {
            "foreign_net_buy": 1200000000,
        },
        "theme_context": [
            {"theme": f"theme_{index}"}
            for index in range(1, 8)
        ],
        "metadata": {
            "gate_score": 0.72,
            "event_ref": "evt_fixture",
            "stub_agent_outputs": {
                "news": {
                    "summary": "업황 뉴스가 단기 모멘텀을 지지합니다.",
                    "stance": "positive",
                    "confidence": 0.81,
                },
            },
        },
    }
    return CandidateEventRequest.model_validate(payload)


def test_build_prompt_renders_news_prompt_with_truncated_context() -> None:
    result = build_prompt("news", build_candidate_event_request())

    assert result.spec.agent_name == "news"
    assert "삼성전자" in result.prompt
    assert '"id": "news_1"' in result.prompt
    assert '"id": "news_5"' in result.prompt
    assert '"id": "news_6"' not in result.prompt
    assert "{candidate_id}" not in result.prompt


def test_build_prompt_renders_editor_prompt_with_specialist_findings() -> None:
    result = build_prompt(
        "editor",
        build_candidate_event_request(),
        specialist_findings=[
            {"agent": "news", "summary": "업황 뉴스가 단기 모멘텀을 지지합니다."},
            {"agent": "risk", "summary": "단기 과열 가능성을 함께 봐야 합니다."},
        ],
    )

    assert result.spec.agent_name == "editor"
    assert '"agent": "news"' in result.prompt
    assert '"agent": "risk"' in result.prompt
    assert '{specialist_findings_json}' not in result.prompt


def test_build_prompt_uses_agent_specific_focus_text() -> None:
    chart_prompt = build_prompt("chart", build_candidate_event_request())
    risk_prompt = build_prompt("risk", build_candidate_event_request())

    assert "technical strength or weakness" in chart_prompt.prompt
    assert "downside scenarios" in risk_prompt.prompt
