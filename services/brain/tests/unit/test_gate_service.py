from __future__ import annotations

from app.config import BrainSettings
from app.contracts.output import SignalDecision
from app.gate.service import GateService


def build_settings(
    briefing_threshold: float = 0.55,
    instant_push_threshold: float = 0.80,
) -> BrainSettings:
    return BrainSettings(
        briefing_threshold=briefing_threshold,
        instant_push_threshold=instant_push_threshold,
    )


def test_evaluate_returns_reject_with_structured_reasons_below_briefing_threshold(
) -> None:
    service = GateService(settings=build_settings())

    result = service.evaluate(score=0.54)

    assert result.decision == SignalDecision.REJECT
    assert result.gate.score == 0.54
    assert result.gate.reason == "score below briefing threshold"
    assert result.reject_reasons == [
        {
            "code": "below_briefing_threshold",
            "message": "score 0.54 is below briefing threshold 0.55",
        },
    ]


def test_evaluate_returns_briefing_at_briefing_threshold() -> None:
    service = GateService(settings=build_settings())

    result = service.evaluate(score=0.55)

    assert result.decision == SignalDecision.BRIEFING
    assert result.gate.score == 0.55
    assert (
        result.gate.reason
        == "score meets briefing threshold but not instant-push threshold"
    )
    assert result.reject_reasons == []


def test_evaluate_returns_instant_push_at_instant_push_threshold() -> None:
    service = GateService(settings=build_settings())

    result = service.evaluate(score=0.80)

    assert result.decision == SignalDecision.INSTANT_PUSH
    assert result.gate.score == 0.80
    assert result.gate.reason == "score meets instant-push threshold"
    assert result.reject_reasons == []


def test_evaluate_uses_settings_thresholds_instead_of_inline_values() -> None:
    service = GateService(
        settings=build_settings(briefing_threshold=0.40, instant_push_threshold=0.90),
    )

    briefing_result = service.evaluate(score=0.40)
    reject_result = service.evaluate(score=0.39)
    instant_push_result = service.evaluate(score=0.90)

    assert briefing_result.decision == SignalDecision.BRIEFING
    assert reject_result.decision == SignalDecision.REJECT
    assert instant_push_result.decision == SignalDecision.INSTANT_PUSH
