from __future__ import annotations

from dataclasses import dataclass

from app.config import BrainSettings, get_settings
from app.contracts.output import GateSummary, SignalDecision


@dataclass(frozen=True)
class RejectReason:
    code: str
    message: str


@dataclass(frozen=True)
class GateEvaluationResult:
    decision: SignalDecision
    gate: GateSummary
    reject_reasons: list[dict[str, str]]


class GateService:
    def __init__(self, settings: BrainSettings | None = None) -> None:
        self._settings = settings or get_settings()

    def evaluate(self, score: float) -> GateEvaluationResult:
        if score >= self._settings.instant_push_threshold:
            return GateEvaluationResult(
                decision=SignalDecision.INSTANT_PUSH,
                gate=GateSummary(
                    score=score,
                    reason="score meets instant-push threshold",
                ),
                reject_reasons=[],
            )

        if score >= self._settings.briefing_threshold:
            return GateEvaluationResult(
                decision=SignalDecision.BRIEFING,
                gate=GateSummary(
                    score=score,
                    reason=(
                        "score meets briefing threshold but not instant-push threshold"
                    ),
                ),
                reject_reasons=[],
            )

        reject_reason = RejectReason(
            code="below_briefing_threshold",
            message=(
                f"score {score:.2f} is below briefing threshold "
                f"{self._settings.briefing_threshold:.2f}"
            ),
        )
        return GateEvaluationResult(
            decision=SignalDecision.REJECT,
            gate=GateSummary(
                score=score,
                reason="score below briefing threshold",
            ),
            reject_reasons=[
                {
                    "code": reject_reason.code,
                    "message": reject_reason.message,
                },
            ],
        )
